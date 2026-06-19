package com.example.guidewirehomesecurityapp.auth

import android.content.Context
import android.content.Intent
import android.provider.Settings
import com.example.guidewirehomesecurityapp.BuildConfig
import androidx.activity.compose.ManagedActivityResultLauncher
import androidx.activity.result.ActivityResult
import androidx.credentials.CredentialManager
import androidx.credentials.CredentialOption
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialException
import androidx.credentials.exceptions.NoCredentialException
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch

class GoogleSignInUtils {
    companion object {
        fun doGoogleSignIn(
            context: Context,
            scope: CoroutineScope,
            launcher: ManagedActivityResultLauncher<Intent, ActivityResult>?,
            signUp: Boolean,
            onSuccess: (String) -> Unit,
            onError: (String) -> Unit
        ){
            val credentialManager = CredentialManager.create(context)
            val request = GetCredentialRequest.Builder()
                .addCredentialOption(getCredentialOptions(context))
                .build()
            scope.launch {
                try {
                    val result = credentialManager.getCredential(context, request)
                    when (result.credential) {
                        is CustomCredential -> {
                            if (result.credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL) {
                                val cred = GoogleIdTokenCredential.createFrom(result.credential.data)
                                val idToken = cred.idToken
                                if (signUp) {
                                    BackendAuthService.signUp(context, idToken, { onSuccess(idToken) }, onError)
                                } else {
                                    // signIn handles MFA internally, onSuccess not used for signin path
                                    onSuccess(idToken)
                                }
                            }
                        }
                    }
                } catch (e: NoCredentialException) {
                    launcher?.launch(getIntent())
                } catch (e: GetCredentialException) {
                    e.printStackTrace()
                }
            }
        }

        fun getIntent(): Intent {
            return Intent(Settings.ACTION_ADD_ACCOUNT).apply {
                putExtra(Settings.EXTRA_ACCOUNT_TYPES, arrayOf("com.google"))
            }
        }

        fun getCredentialOptions(context: Context): CredentialOption {
            // Server client ID from frontend/local.properties (GOOGLE_CLIENT_ID) via BuildConfig
            return GetGoogleIdOption.Builder()
                .setFilterByAuthorizedAccounts(false)
                .setAutoSelectEnabled(false)
                .setServerClientId(BuildConfig.GOOGLE_CLIENT_ID)
                .build()
        }
    }
}
