// AntBarter Authentication using AWS Cognito

class AntBarterAuth {
    constructor() {
        this.poolData = {
            UserPoolId: awsConfig.userPoolId,
            ClientId: awsConfig.userPoolWebClientId
        };
        this.userPool = new AmazonCognitoIdentity.CognitoUserPool(this.poolData);
        this.currentUser = null;
    }

    // Simple sign up function
    signUp(email, password, fullName, callback) {
        const attributeList = [
            new AmazonCognitoIdentity.CognitoUserAttribute({
                Name: 'email',
                Value: email
            }),
            new AmazonCognitoIdentity.CognitoUserAttribute({
                Name: 'name',
                Value: fullName
            })
        ];

        this.userPool.signUp(email, password, attributeList, null, (err, result) => {
            if (err) {
                console.error('Sign up error:', err);
                callback(err, null);
                return;
            }
            console.log('User signed up successfully');
            callback(null, result.user);
        });
    }

    // Simple sign in function
    signIn(email, password, callback) {
        const authenticationData = {
            Username: email,
            Password: password
        };

        const authenticationDetails = new AmazonCognitoIdentity.AuthenticationDetails(authenticationData);
        
        const userData = {
            Username: email,
            Pool: this.userPool
        };

        const cognitoUser = new AmazonCognitoIdentity.CognitoUser(userData);

        cognitoUser.authenticateUser(authenticationDetails, {
            onSuccess: (result) => {
                console.log('Sign in successful');
                this.currentUser = cognitoUser;
                callback(null, result);
            },
            onFailure: (err) => {
                console.error('Sign in error:', err);
                callback(err, null);
            }
        });
    }

    // Check if user is signed in
    getCurrentUser() {
        return this.userPool.getCurrentUser();
    }

    // Sign out
    signOut() {
        const cognitoUser = this.getCurrentUser();
        if (cognitoUser) {
            cognitoUser.signOut();
            this.currentUser = null;
        }
    }
}

// Initialize authentication
const antBarterAuth = new AntBarterAuth();