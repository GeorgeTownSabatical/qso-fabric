export class QSOClient {
  constructor(baseUrl = "http://localhost:8000") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async createIdentity(identityId, immutableCore, actor = "authority", policyVersion = "v1") {
    return this.#post("/v1/identity/create", {
      identity_id: identityId,
      immutable_core: immutableCore,
      actor,
      policy_version: policyVersion,
    });
  }

  async mutateIdentity(identityId, delta, actor = "authority", policyVersion = "v1") {
    return this.#post("/v1/identity/mutate", {
      identity_id: identityId,
      delta,
      actor,
      policy_version: policyVersion,
    });
  }

  async revokeIdentity(identityId, reason, actor = "authority", policyVersion = "v1") {
    return this.#post("/v1/identity/revoke", {
      identity_id: identityId,
      reason,
      actor,
      policy_version: policyVersion,
    });
  }

  async currentPolicy() {
    const response = await fetch(`${this.baseUrl}/v1/policy/current`);
    if (!response.ok) {
      throw new Error(`policy current failed: ${response.status}`);
    }
    return response.json();
  }

  async #post(path, payload) {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body.error || `${path} failed: ${response.status}`);
    }
    return body;
  }
}
