# MongoDB Atlas Setup Guide

## Step 1: Create MongoDB Atlas Account

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register)
2. Sign up for a free account
3. Verify your email

## Step 2: Create a Cluster

1. Click "Build a Database"
2. Choose **FREE** tier (M0 Sandbox)
3. Select your preferred cloud provider and region
4. Click "Create Cluster" (takes 1-3 minutes)

## Step 3: Create Database User

1. In the left sidebar, click "Database Access"
2. Click "Add New Database User"
3. Choose "Password" authentication
4. Enter username and password (save these!)
5. Set privileges to "Read and write to any database"
6. Click "Add User"

## Step 4: Configure Network Access

1. In the left sidebar, click "Network Access"
2. Click "Add IP Address"
3. Click "Allow Access from Anywhere" (for development)
   - Or add your specific IP address for better security
4. Click "Confirm"

## Step 5: Get Connection String

1. Go back to "Database" in the left sidebar
2. Click "Connect" on your cluster
3. Choose "Connect your application"
4. Select "Python" and version "3.12 or later"
5. Copy the connection string (looks like this):
   ```
   mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
6. Replace `<username>` and `<password>` with your database user credentials

## Step 6: Update .env File

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and update:
   ```
   MONGODB_URL=mongodb+srv://your-username:your-password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   DATABASE_NAME=aiboomi_mentora
   SECRET_KEY=generate-a-random-secret-key
   ```

3. Generate a secure SECRET_KEY:
   ```bash
   # On Windows PowerShell:
   -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})
   
   # Or use any random 32+ character string
   ```

## Step 7: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## Step 8: Run the Server

```bash
uvicorn main:app --reload
```

You should see:
```
✅ Successfully connected to MongoDB Atlas!
✅ Database indexes created successfully
```

## Troubleshooting

### Connection Error
- Check your username/password in the connection string
- Verify Network Access allows your IP
- Make sure you replaced `<username>` and `<password>` in the connection string

### Authentication Error
- Ensure database user has correct permissions
- Check that password doesn't contain special characters (or URL-encode them)

### Index Creation Error
- This is usually fine on first run
- Indexes will be created automatically

## Next Steps

Once connected, you can:
1. Test the API at `http://localhost:8000/docs`
2. Register a new user
3. Login and get an access token
4. Use the token to access protected endpoints
