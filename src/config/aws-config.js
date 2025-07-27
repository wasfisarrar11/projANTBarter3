// AWS Cognito Configuration for AntBarter
const awsConfig = {
    region: 'us-east-2', // Replace with your region
    userPoolId: 'https://us-east-23zksjjhno.auth.us-east-2.amazoncognito.com/',

    // Replace with your User Pool ID
    userPoolWebClientId: '2n275r257gtqo1vg7799aarovh', // Replace with your App Client ID
    
    // TODO: If you set up Identity Pool later
    identityPoolId: '', // Leave empty for now
    
    // App specific settings
    cookieStorage: {
        domain: 'localhost', // Change to your domain when deployed
        path: '/',
        expires: 365,
        secure: false // Set to true in production with HTTPS
    }
};

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = awsConfig;
} else {
    window.awsConfig = awsConfig;
}