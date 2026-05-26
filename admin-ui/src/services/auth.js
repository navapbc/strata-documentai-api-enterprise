// Cognito auth service - sign up, confirm, sign in, sign out

const COGNITO_REGION = "us-east-1";
let _userPoolId = null;
let _clientId = null;

export function configure(userPoolId, clientId) {
  _userPoolId = userPoolId;
  _clientId = clientId;
}

async function cognitoFetch(action, body) {
  const response = await fetch(`https://cognito-idp.${COGNITO_REGION}.amazonaws.com/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-amz-json-1.1",
      "X-Amz-Target": `AWSCognitoIdentityProviderService.${action}`,
    },
    body: JSON.stringify(body),
  });

  const data = await response.json();

  if (!response.ok) {
    const error = new Error(data.message || data.__type || "Cognito error");
    error.code = data.__type;
    throw error;
  }

  return data;
}

export async function signUp(email, password) {
  return cognitoFetch("SignUp", {
    ClientId: _clientId,
    Username: email,
    Password: password,
    UserAttributes: [{ Name: "email", Value: email }],
  });
}

export async function confirmSignUp(email, code) {
  return cognitoFetch("ConfirmSignUp", {
    ClientId: _clientId,
    Username: email,
    ConfirmationCode: code,
  });
}

export async function signIn(email, password) {
  const result = await cognitoFetch("InitiateAuth", {
    AuthFlow: "USER_PASSWORD_AUTH",
    ClientId: _clientId,
    AuthParameters: {
      USERNAME: email,
      PASSWORD: password,
    },
  });

  // MFA challenge - return challenge info for the caller to handle
  if (result.ChallengeName) {
    return {
      challenge: result.ChallengeName,
      session: result.Session,
    };
  }

  return {
    accessToken: result.AuthenticationResult.AccessToken,
    idToken: result.AuthenticationResult.IdToken,
    refreshToken: result.AuthenticationResult.RefreshToken,
    expiresIn: result.AuthenticationResult.ExpiresIn,
  };
}

export async function respondToMfaChallenge(session, code, email) {
  const result = await cognitoFetch("RespondToAuthChallenge", {
    ClientId: _clientId,
    ChallengeName: "SOFTWARE_TOKEN_MFA",
    Session: session,
    ChallengeResponses: {
      USERNAME: email,
      SOFTWARE_TOKEN_MFA_CODE: code,
    },
  });

  return {
    accessToken: result.AuthenticationResult.AccessToken,
    idToken: result.AuthenticationResult.IdToken,
    refreshToken: result.AuthenticationResult.RefreshToken,
    expiresIn: result.AuthenticationResult.ExpiresIn,
  };
}

export async function associateSoftwareToken(session) {
  return cognitoFetch("AssociateSoftwareToken", {
    Session: session,
  });
}

export async function verifySoftwareToken(session, code, email) {
  const result = await cognitoFetch("VerifySoftwareToken", {
    Session: session,
    UserCode: code,
    FriendlyDeviceName: "Authenticator",
  });

  // After setup verification, respond to the MFA_SETUP challenge to complete auth
  if (result.Session) {
    const authResult = await cognitoFetch("RespondToAuthChallenge", {
      ClientId: _clientId,
      ChallengeName: "MFA_SETUP",
      Session: result.Session,
      ChallengeResponses: {
        USERNAME: email,
      },
    });
    return {
      accessToken: authResult.AuthenticationResult.AccessToken,
      idToken: authResult.AuthenticationResult.IdToken,
      refreshToken: authResult.AuthenticationResult.RefreshToken,
      expiresIn: authResult.AuthenticationResult.ExpiresIn,
    };
  }
  return result;
}

export async function refreshSession(refreshToken) {
  const result = await cognitoFetch("InitiateAuth", {
    AuthFlow: "REFRESH_TOKEN_AUTH",
    ClientId: _clientId,
    AuthParameters: {
      REFRESH_TOKEN: refreshToken,
    },
  });

  return {
    accessToken: result.AuthenticationResult.AccessToken,
    idToken: result.AuthenticationResult.IdToken,
    expiresIn: result.AuthenticationResult.ExpiresIn,
  };
}

export async function signOut(accessToken) {
  return cognitoFetch("GlobalSignOut", {
    AccessToken: accessToken,
  });
}

export async function forgotPassword(email) {
  return cognitoFetch("ForgotPassword", {
    ClientId: _clientId,
    Username: email,
  });
}

export async function confirmForgotPassword(email, code, newPassword) {
  return cognitoFetch("ConfirmForgotPassword", {
    ClientId: _clientId,
    Username: email,
    ConfirmationCode: code,
    Password: newPassword,
  });
}
