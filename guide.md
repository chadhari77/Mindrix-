# Firebase Setup Guide for College Management System

## Step 1: Create Firebase Project

### 1.1 Access Firebase Console
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Sign in with your Google account
3. Click **"Create a project"** or **"Add project"**

### 1.2 Project Configuration
1. **Project name**: Enter "College Management System" (or your preferred name)
2. **Project ID**: Firebase will auto-generate one, or customize it
3. **Analytics**: Choose whether to enable Google Analytics (recommended for tracking)
4. If Analytics enabled, select or create an Analytics account
5. Click **"Create project"**
6. Wait for project creation to complete

## Step 2: Enable Authentication

### 2.1 Set Up Authentication
1. In your Firebase project dashboard, click **"Authentication"** in the left sidebar
2. Click **"Get started"**
3. Go to the **"Sign-in method"** tab

### 2.2 Enable Email/Password Authentication
1. Click on **"Email/Password"** provider
2. Toggle **"Enable"** to ON
3. **Email link (passwordless sign-in)**: Leave disabled for now
4. Click **"Save"**

### 2.3 Configure Authorized Domains (Optional)
1. In the **"Sign-in method"** tab, scroll down to **"Authorized domains"**
2. Add your domain(s) where the app will be hosted:
   - `localhost` (for development)
   - Your production domain (e.g., `yourapp.com`)

## Step 3: Set Up Firestore Database

### 3.1 Create Firestore Database
1. Click **"Firestore Database"** in the left sidebar
2. Click **"Create database"**
3. **Security rules**: Choose **"Start in test mode"** for development
   - This allows read/write access for 30 days
   - You'll need to update rules later for production
4. **Location**: Choose a location closest to your users
5. Click **"Next"** and then **"Done"**

### 3.2 Create Initial Collections
Create these collections for your project:

#### Users Collection
1. Click **"Start collection"**
2. Collection ID: `users`
3. Add a sample document:
   ```json
   Document ID: (auto-generated)
   Fields:
   - email: string
   - user_type: string (student/faculty/admin)
   - full_name: string
   - created_at: timestamp
   - active: boolean
   ```

#### Students Collection
1. Create collection: `students`
2. Sample document structure:
   ```json
   Document ID: (auto-generated)
   Fields:
   - user_id: string (reference to users collection)
   - student_id: string
   - section: string
   - department: string
   - year: number
   ```

#### Faculty Collection
1. Create collection: `faculty`
2. Sample document structure:
   ```json
   Document ID: (auto-generated)
   Fields:
   - user_id: string
   - employee_id: string
   - department: string
   - subjects: array
   ```

#### Notes Collection
1. Create collection: `notes`
2. Sample document structure:
   ```json
   Document ID: (auto-generated)
   Fields:
   - title: string
   - filename: string
   - uploaded_by: string
   - department: string
   - subject: string
   - upload_date: timestamp
   - file_path: string
   ```

## Step 4: Configure Storage

### 4.1 Enable Cloud Storage
1. Click **"Storage"** in the left sidebar
2. Click **"Get started"**
3. **Security rules**: Start in test mode
4. **Location**: Choose same location as Firestore
5. Click **"Done"**

### 4.2 Create Storage Folders
1. In Storage, create these folders:
   - `notes/` (for uploaded notes)
   - `documents/` (for other documents)
   - `uploads/` (for general uploads)

## Step 5: Get Configuration Keys

### 5.1 Generate Web App Configuration
1. In Project Overview, click the **"Web"** icon (`</>`)
2. **App nickname**: "College Management Web App"
3. **Firebase Hosting**: Check this if you plan to use Firebase hosting
4. Click **"Register app"**

### 5.2 Copy Configuration
You'll get a configuration object like this:
```javascript
const firebaseConfig = {
  apiKey: "your-api-key",
  authDomain: "your-project.firebaseapp.com",
  projectId: "your-project-id",
  storageBucket: "your-project.appspot.com",
  messagingSenderId: "123456789",
  appId: "your-app-id"
};
```

### 5.3 Generate Service Account Key
1. Click the **gear icon** ⚙️ next to "Project Overview"
2. Select **"Project settings"**
3. Go to **"Service accounts"** tab
4. Click **"Generate new private key"**
5. Click **"Generate key"** - this downloads a JSON file
6. **Important**: Keep this file secure and never commit it to version control

## Step 6: Create Configuration Files

### 6.1 Create Firebase Config File
Create `config/firebase_config.json` with your service account key:
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "your-private-key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-xxxxx@your-project.iam.gserviceaccount.com",
  "client_id": "your-client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-xxxxx%40your-project.iam.gserviceaccount.com"
}
```

### 6.2 Update Environment Variables
Create/update your `.env` file:
```env
FIREBASE_CONFIG_PATH=config/firebase_config.json
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
GROQ_API_KEY=your_groq_api_key
N8N_WEBHOOK_URL=your_n8n_webhook_url
MULTICHAIN_RPC_URL=your_multichain_rpc_url
SECRET_KEY=your-secret-key-here
```

## Step 7: Set Up Security Rules

### 7.1 Firestore Security Rules
1. Go to **Firestore Database** → **Rules**
2. Replace the default rules with:
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can read/write their own user document
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Students can read their own student document
    match /students/{studentId} {
      allow read, write: if request.auth != null && 
        resource.data.user_id == request.auth.uid;
    }
    
    // Faculty can read their own faculty document
    match /faculty/{facultyId} {
      allow read, write: if request.auth != null && 
        resource.data.user_id == request.auth.uid;
    }
    
    // Notes - faculty can write, students can read
    match /notes/{noteId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && 
        exists(/databases/$(database)/documents/faculty/$(request.auth.uid));
    }
  }
}
```

### 7.2 Storage Security Rules
1. Go to **Storage** → **Rules**
2. Replace with:
```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    // Allow authenticated users to upload notes
    match /notes/{allPaths=**} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && 
        request.auth.token.user_type == 'faculty';
    }
    
    // Allow authenticated users to upload documents
    match /documents/{allPaths=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

## Step 8: Test Configuration

### 8.1 Test Firebase Connection
Create a test script `test_firebase.py`:
```python
import firebase_admin
from firebase_admin import credentials, firestore
import os

# Test Firebase connection
cred = credentials.Certificate('config/firebase_config.json')
firebase_admin.initialize_app(cred)

db = firestore.client()

# Test write
doc_ref = db.collection('test').document('test_doc')
doc_ref.set({'test': 'Hello Firebase!'})

# Test read
doc = doc_ref.get()
if doc.exists:
    print(f"Test successful: {doc.to_dict()}")
else:
    print("Test failed: Document not found")

# Clean up
doc_ref.delete()
print("Test completed and cleaned up")
```

Run the test:
```bash
python test_firebase.py
```

## Step 9: Production Considerations

### 9.1 Security Rules for Production
Update Firestore rules for production:
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // More restrictive rules for production
    match /users/{userId} {
      allow read: if request.auth != null && request.auth.uid == userId;
      allow write: if request.auth != null && request.auth.uid == userId && 
        validateUserData(request.resource.data);
    }
    
    // Add validation functions
    function validateUserData(data) {
      return data.keys().hasAll(['email', 'user_type', 'full_name']) &&
             data.user_type in ['student', 'faculty', 'admin'];
    }
  }
}
```

### 9.2 Environment Security
1. Never commit `firebase_config.json` to version control
2. Add to `.gitignore`:
```
config/firebase_config.json
.env
uploads/
*.pyc
__pycache__/
```

### 9.3 Enable Firebase Security Features
1. **App Check**: Enable in Firebase Console → App Check
2. **Security Rules**: Review and test all rules
3. **Monitoring**: Set up alerts for unusual activity

## Step 10: Integration with Your Flask App

Your Flask app should now work with the Firebase configuration. The `utils/firebase_config.py` file should handle the initialization using the service account key.

## Troubleshooting

### Common Issues:
1. **Permission Denied**: Check security rules
2. **Service Account Issues**: Verify the JSON file path and permissions
3. **Network Issues**: Ensure Firebase SDKs are properly installed
4. **Storage Upload Fails**: Check storage rules and bucket permissions

### Debug Steps:
1. Check Firebase Console logs
2. Verify environment variables
3. Test with Firebase emulator for development
4. Check network connectivity and firewall settings

## Next Steps
1. Test user registration and login
2. Upload sample notes and test the RAG system
3. Set up email notifications
4. Configure room allocation features
5. Implement the complaint system

Your Firebase setup is now complete and ready for integration with your College Management System!