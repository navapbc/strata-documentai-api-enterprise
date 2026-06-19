import { describe, it, expect, beforeEach, vi } from "vitest";

let Auth;

describe("auth service", () => {
  beforeEach(async () => {
    vi.resetModules();
    global.fetch = vi.fn();
    Auth = await import("../../src/services/auth.js");
    Auth.configure("us-east-1_TestPool", "test-client-id");
  });

  describe("signIn", () => {
    it("calls InitiateAuth with correct params", async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            AuthenticationResult: {
              AccessToken: "at",
              IdToken: "it",
              RefreshToken: "rt",
              ExpiresIn: 3600,
            },
          }),
      });

      const result = await Auth.signIn("user@test.com", "password123");

      expect(global.fetch).toHaveBeenCalledWith(
        "https://cognito-idp.us-east-1.amazonaws.com/",
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
          }),
        }),
      );

      const body = JSON.parse(global.fetch.mock.calls[0][1].body);
      expect(body.ClientId).toBe("test-client-id");
      expect(body.AuthParameters.USERNAME).toBe("user@test.com");
      expect(body.AuthParameters.PASSWORD).toBe("password123");

      expect(result.accessToken).toBe("at");
      expect(result.idToken).toBe("it");
    });

    it("returns challenge when MFA required", async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            ChallengeName: "SOFTWARE_TOKEN_MFA",
            Session: "session-123",
          }),
      });

      const result = await Auth.signIn("user@test.com", "pass");
      expect(result.challenge).toBe("SOFTWARE_TOKEN_MFA");
      expect(result.session).toBe("session-123");
    });

    it("returns challenge for MFA_SETUP", async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            ChallengeName: "MFA_SETUP",
            Session: "setup-session",
          }),
      });

      const result = await Auth.signIn("user@test.com", "pass");
      expect(result.challenge).toBe("MFA_SETUP");
    });

    it("throws on Cognito error", async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        json: () =>
          Promise.resolve({
            __type: "NotAuthorizedException",
            message: "Incorrect username or password",
          }),
      });

      await expect(Auth.signIn("user@test.com", "wrong")).rejects.toThrow(
        "Incorrect username or password",
      );
    });

    it("error has code property", async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        json: () =>
          Promise.resolve({
            __type: "UserNotFoundException",
            message: "User not found",
          }),
      });

      const err = await Auth.signIn("nobody@test.com", "pass").catch((e) => e);
      expect(err.code).toBe("UserNotFoundException");
    });
  });

  describe("respondToMfaChallenge", () => {
    it("calls RespondToAuthChallenge with correct params", async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            AuthenticationResult: {
              AccessToken: "at",
              IdToken: "it",
              RefreshToken: "rt",
              ExpiresIn: 3600,
            },
          }),
      });

      const result = await Auth.respondToMfaChallenge("session-1", "123456", "user@test.com");

      const body = JSON.parse(global.fetch.mock.calls[0][1].body);
      expect(body.ChallengeName).toBe("SOFTWARE_TOKEN_MFA");
      expect(body.ChallengeResponses.USERNAME).toBe("user@test.com");
      expect(body.ChallengeResponses.SOFTWARE_TOKEN_MFA_CODE).toBe("123456");
      expect(result.accessToken).toBe("at");
    });
  });

  describe("signUp", () => {
    it("calls SignUp with email as username", async () => {
      global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });

      await Auth.signUp("new@test.com", "password123");

      const body = JSON.parse(global.fetch.mock.calls[0][1].body);
      expect(body.Username).toBe("new@test.com");
      expect(body.Password).toBe("password123");
      expect(body.UserAttributes[0]).toEqual({ Name: "email", Value: "new@test.com" });
    });
  });

  describe("signOut", () => {
    it("calls GlobalSignOut with access token", async () => {
      global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });

      await Auth.signOut("my-access-token");

      const body = JSON.parse(global.fetch.mock.calls[0][1].body);
      expect(body.AccessToken).toBe("my-access-token");
      expect(global.fetch.mock.calls[0][1].headers["X-Amz-Target"]).toBe(
        "AWSCognitoIdentityProviderService.GlobalSignOut",
      );
    });
  });

  describe("refreshSession", () => {
    it("calls InitiateAuth with REFRESH_TOKEN_AUTH", async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            AuthenticationResult: {
              AccessToken: "new-at",
              IdToken: "new-it",
              ExpiresIn: 3600,
            },
          }),
      });

      const result = await Auth.refreshSession("my-refresh-token");

      const body = JSON.parse(global.fetch.mock.calls[0][1].body);
      expect(body.AuthFlow).toBe("REFRESH_TOKEN_AUTH");
      expect(body.AuthParameters.REFRESH_TOKEN).toBe("my-refresh-token");
      expect(result.accessToken).toBe("new-at");
    });
  });
});

describe("auth service - additional coverage", () => {
  beforeEach(async () => {
    vi.resetModules();
    global.fetch = vi.fn();
    Auth = await import("../../src/services/auth.js");
    Auth.configure("us-east-1_TestPool", "test-client-id");
  });

  it("sends Content-Type application/x-amz-json-1.1", async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          AuthenticationResult: {
            AccessToken: "a",
            IdToken: "i",
            RefreshToken: "r",
            ExpiresIn: 60,
          },
        }),
    });
    await Auth.signIn("u@t.com", "p");
    expect(global.fetch.mock.calls[0][1].headers["Content-Type"]).toBe(
      "application/x-amz-json-1.1",
    );
  });

  it("confirmSignUp calls ConfirmSignUp action", async () => {
    global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
    await Auth.confirmSignUp("u@t.com", "123456");
    const body = JSON.parse(global.fetch.mock.calls[0][1].body);
    expect(body.Username).toBe("u@t.com");
    expect(body.ConfirmationCode).toBe("123456");
    expect(global.fetch.mock.calls[0][1].headers["X-Amz-Target"]).toBe(
      "AWSCognitoIdentityProviderService.ConfirmSignUp",
    );
  });

  it("associateSoftwareToken calls correct action", async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ SecretCode: "ABCDEF", Session: "s2" }),
    });
    const result = await Auth.associateSoftwareToken("session-1");
    const body = JSON.parse(global.fetch.mock.calls[0][1].body);
    expect(body.Session).toBe("session-1");
    expect(result.SecretCode).toBe("ABCDEF");
  });

  it("verifySoftwareToken calls VerifySoftwareToken then RespondToAuthChallenge", async () => {
    // First call: VerifySoftwareToken returns a session
    // Second call: RespondToAuthChallenge returns tokens
    global.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ Session: "verified-session" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            AuthenticationResult: {
              AccessToken: "at",
              IdToken: "it",
              RefreshToken: "rt",
              ExpiresIn: 3600,
            },
          }),
      });

    const result = await Auth.verifySoftwareToken("setup-session", "123456", "u@t.com");

    // First call is VerifySoftwareToken
    const body1 = JSON.parse(global.fetch.mock.calls[0][1].body);
    expect(body1.UserCode).toBe("123456");
    expect(body1.Session).toBe("setup-session");

    // Second call is RespondToAuthChallenge (MFA_SETUP)
    const body2 = JSON.parse(global.fetch.mock.calls[1][1].body);
    expect(body2.ChallengeName).toBe("MFA_SETUP");
    expect(body2.ChallengeResponses.USERNAME).toBe("u@t.com");

    expect(result.accessToken).toBe("at");
  });

  it("error uses __type as fallback message", async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ __type: "LimitExceededException" }),
    });
    await expect(Auth.signIn("u@t.com", "p")).rejects.toThrow("LimitExceededException");
  });

  it("error falls back to 'Cognito error' when no message or type", async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({}),
    });
    await expect(Auth.signIn("u@t.com", "p")).rejects.toThrow("Cognito error");
  });
});
