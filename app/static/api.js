/*
  Character Consistency Workbench: the client for the workbench server

  Every path the screens use lives here, so app.js never calls fetch. A
  plain script like app.js, loaded just before it. Each function returns a
  promise of the server's JSON, or rejects with an ApiError whose message
  can be shown to the creator as it is. A live turn streams as server-sent
  events: stream() hands each event to onEvent as it arrives.
*/
window.WorkbenchApi = (() => {
  "use strict";

  class ApiError extends Error {
    constructor(status, message, field = null, problems = []) {
      super(message);
      this.name = "ApiError";
      this.status = status; // 0 when the server didn't answer
      this.field = field; // the draft field to fix, when the server names one
      this.problems = problems; // rows to fix in an import, as { row, message }
    }
  }

  const UNREACHABLE = "Couldn't reach the workbench server. Check that app/run.sh is still running.";
  const DROPPED = "The connection to the workbench server dropped. Reload to see the saved reply.";

  // One ID per browser tab, kept across reloads, so the server can tell
  // sessions apart in its logs.
  function sessionId() {
    const key = "workbench-session";
    try {
      const saved = sessionStorage.getItem(key);
      if (saved) return saved;
    } catch {
      // Storage can be off. A fresh ID per load still works.
    }
    let id;
    if (crypto.randomUUID) {
      id = crypto.randomUUID();
    } else {
      const bytes = crypto.getRandomValues(new Uint8Array(16));
      bytes[6] = (bytes[6] & 0x0f) | 0x40;
      bytes[8] = (bytes[8] & 0x3f) | 0x80;
      const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
      id = `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
    }
    try {
      sessionStorage.setItem(key, id);
    } catch {
      // See above.
    }
    return id;
  }

  const SESSION = sessionId();

  function options(method, body, accept) {
    const init = { method, headers: { Accept: accept, "X-Workbench-Session": SESSION } };
    if (body !== undefined) {
      // The server only reads a body sent with this content type.
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }
    return init;
  }

  async function failure(response) {
    const data = await response.json().catch(() => null);
    const message = data && typeof data.detail === "string"
      ? data.detail
      : "Something went wrong on the server. Try again.";
    return new ApiError(response.status, message, data && data.field ? data.field : null, (data && data.problems) || []);
  }

  async function request(method, path, body) {
    let response;
    try {
      response = await fetch(path, options(method, body, "application/json"));
    } catch {
      throw new ApiError(0, UNREACHABLE);
    }
    if (!response.ok) throw await failure(response);
    return response.json().catch(() => null);
  }

  // One server-sent event block, as onEvent(name, data). Comment lines (the
  // server's keep-alive pings) and blocks without data are skipped.
  function dispatch(block, onEvent) {
    let name = "message";
    const data = [];
    block.split("\n").forEach((line) => {
      if (!line || line.startsWith(":")) return;
      const colon = line.indexOf(":");
      const field = colon === -1 ? line : line.slice(0, colon);
      let value = colon === -1 ? "" : line.slice(colon + 1);
      if (value.startsWith(" ")) value = value.slice(1);
      if (field === "event") name = value;
      else if (field === "data") data.push(value);
    });
    if (data.length === 0) return null;
    const payload = JSON.parse(data.join("\n"));
    onEvent(name, payload);
    return name;
  }

  // POSTs and reads the reply as a stream of events. Resolves when the
  // stream ends with done or error. An abort rejects with the AbortError
  // itself, so callers can ignore it.
  async function stream(path, body, onEvent, signal) {
    let response;
    try {
      response = await fetch(path, { ...options("POST", body, "text/event-stream"), signal });
    } catch (error) {
      if (error && error.name === "AbortError") throw error;
      throw new ApiError(0, UNREACHABLE);
    }
    if (!response.ok) throw await failure(response);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let last = null;
    try {
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        buffer = buffer.replace(/\r\n?/g, "\n");
        let end = buffer.indexOf("\n\n");
        while (end !== -1) {
          last = dispatch(buffer.slice(0, end), onEvent) || last;
          buffer = buffer.slice(end + 2);
          end = buffer.indexOf("\n\n");
        }
      }
      buffer += decoder.decode();
      if (buffer.trim()) last = dispatch(buffer.replace(/\r\n?/g, "\n"), onEvent) || last;
    } catch (error) {
      if (error && error.name === "AbortError") throw error;
      if (error instanceof ApiError) throw error;
      throw new ApiError(0, DROPPED);
    }
    if (last !== "done" && last !== "error") throw new ApiError(0, DROPPED);
  }

  const part = encodeURIComponent;

  return {
    ApiError,
    listCharacters: () => request("GET", "/api/characters"),
    // version is a number, or "latest".
    getSpec: (slug, version = "latest") => request("GET", `/api/characters/${part(slug)}/specs/${part(version)}`),
    saveSpec: (slug, edit) => request("POST", `/api/characters/${part(slug)}/specs`, edit),

    // Run a conversation.
    runOptions: () => request("GET", "/api/run-options"),
    listChats: () => request("GET", "/api/chats"),
    getChat: (id) => request("GET", `/api/chats/${part(id)}`),
    startChat: (start) => request("POST", "/api/chats", start),
    // The next scripted line, or the line still waiting for a reply.
    nextTurn: (id, onEvent, signal) => stream(`/api/chats/${part(id)}/next`, undefined, onEvent, signal),
    sendMessage: (id, text, onEvent, signal) => stream(`/api/chats/${part(id)}/messages`, { text }, onEvent, signal),
    stopChat: (id) => request("POST", `/api/chats/${part(id)}/stop`),
    // The saved check of a chat as it stands, as { running, result }. Never calls a model.
    getCheck: (id) => request("GET", `/api/chats/${part(id)}/check`),
    // Runs the automatic checks and the AI judge, or returns the saved check when one covers the chat.
    checkChat: (id) => request("POST", `/api/chats/${part(id)}/check`),

    // Flag review. getReview returns every checked chat with its flags and the
    // creator's calls. Each call returns the flag's chat as it now stands.
    getReview: () => request("GET", "/api/review"),
    openEvidence: (flagId) => request("POST", `/api/flags/${part(flagId)}/evidence`),
    agreeFlag: (flagId) => request("POST", `/api/flags/${part(flagId)}/agree`),
    // type is the right failure type, or null when the flag isn't a break.
    overrideFlag: (flagId, reason, type) => request("POST", `/api/flags/${part(flagId)}/override`, { reason, type }),
    undoCall: (flagId) => request("POST", `/api/flags/${part(flagId)}/undo`),
    // The follow-up re-check of a chat's saved check, with the creator's
    // question or null. Returns the chat's review as it now stands.
    recheckChat: (chatId, question) => request("POST", `/api/chats/${part(chatId)}/recheck`, { question }),

    // Import.
    listSamples: () => request("GET", "/api/samples"),
    previewImport: (body) => request("POST", "/api/imports/preview", body),
    importChat: (body) => request("POST", "/api/imports", body),
  };
})();
