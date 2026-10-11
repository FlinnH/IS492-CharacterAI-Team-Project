/*
  Character Consistency Workbench: the client for the workbench server

  Every path the screens use lives here, so app.js never calls fetch. A
  plain script like app.js, loaded just before it. Each function returns a
  promise of the server's JSON, or rejects with an ApiError whose message
  can be shown to the creator as it is.
*/
window.WorkbenchApi = (() => {
  "use strict";

  class ApiError extends Error {
    constructor(status, message, field = null) {
      super(message);
      this.name = "ApiError";
      this.status = status; // 0 when the server didn't answer
      this.field = field; // the draft field to fix, when the server names one
    }
  }

  async function request(method, path, body) {
    const options = { method, headers: { Accept: "application/json" } };
    if (body !== undefined) {
      // The server only reads a body sent with this content type.
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }

    let response;
    try {
      response = await fetch(path, options);
    } catch {
      throw new ApiError(0, "Couldn't reach the workbench server. Check that app/run.sh is still running.");
    }

    const data = await response.json().catch(() => null);
    if (!response.ok) {
      const message = data && typeof data.detail === "string"
        ? data.detail
        : "Something went wrong on the server. Try again.";
      throw new ApiError(response.status, message, data && data.field ? data.field : null);
    }
    return data;
  }

  const part = encodeURIComponent;

  return {
    ApiError,
    listCharacters: () => request("GET", "/api/characters"),
    // version is a number, or "latest".
    getSpec: (slug, version = "latest") => request("GET", `/api/characters/${part(slug)}/specs/${part(version)}`),
    saveSpec: (slug, edit) => request("POST", `/api/characters/${part(slug)}/specs`, edit),
  };
})();
