# Setting Up TikTok Official Third-Party API Access

This guide will help you set up TikTok's official third-party data transfer API for your collector.

## Prerequisites

- You must be located in the **European Economic Area (EEA)** or **United Kingdom (UK)** to use this feature
- A TikTok account
- Basic understanding of OAuth flows

## Step-by-Step Setup

### 1. Create TikTok Developer Account

1. Go to https://developers.tiktok.com/
2. Click **"Sign Up"** or **"Log In"**
3. Complete the registration process

### 2. Register Your Application

1. In the Developer Dashboard, click **"Manage Apps"** → **"Connect an App"**
2. Fill in your application details:
   - **App Name**: e.g., "TikTok Video Collector"
   - **Description**: e.g., "Personal tool to download and archive saved TikTok videos"
   - **Category**: Select "Personal Use" or appropriate category
   - **Website URL**: Your website (or use a placeholder like `http://localhost`)
   - **App Icon**: Upload an icon (optional)
3. Submit your application for review
   - **Note**: Approval may take a few days

### 3. Configure API Products

Once your app is approved:

1. Go to your app's settings
2. Navigate to **"Products"** or **"API Products"**
3. Add the following products:
   - **Login Kit** (for OAuth authentication)
   - **Data Portability API** (for accessing saved/favorite videos)
   - **Video List API** (if available)

### 4. Set Up OAuth Redirect URI

1. In your app settings, find **"Redirect URI"** or **"Callback URL"**
2. Add: `http://localhost:8080/callback`
3. Save the changes

### 5. Get Your Credentials

1. In your app dashboard, find:
   - **Client Key** (also called App ID)
   - **Client Secret** (keep this secure!)
2. Copy these values

### 6. Update config.ini

Open `config.ini` and add your credentials:

```ini
TIKTOK_CLIENT_KEY = your_client_key_here
TIKTOK_CLIENT_SECRET = your_client_secret_here
TIKTOK_REDIRECT_URI = http://localhost:8080/callback
TIKTOK_SCOPE = user.info.basic,video.list
```

### 7. Run the Collector

```powershell
cd "C:\Users\tombo\GitHub\TikTok Downloader"
.\venv\Scripts\activate
python tiktok_official_api.py
```

The first time you run it:
1. A browser window will open asking you to authorize the app
2. Log in with your TikTok account
3. Grant the requested permissions
4. You'll be redirected back to `http://localhost:8080/callback`
5. The collector will automatically exchange the authorization code for an access token
6. Videos will start downloading

## Troubleshooting

### "API access denied" or 403 errors

- Make sure your app has **Data Portability API** product enabled
- Verify your app has been **approved** by TikTok (not just submitted)
- Check that you're requesting the correct scopes in `config.ini`

### "Invalid redirect URI"

- Make sure the redirect URI in `config.ini` exactly matches what you set in the TikTok Developer Dashboard
- The URI must be `http://localhost:8080/callback` (or whatever port you configured)

### "Client Key/Secret not found"

- Double-check that `TIKTOK_CLIENT_KEY` and `TIKTOK_CLIENT_SECRET` are set in `config.ini`
- Make sure there are no extra spaces or quotes

### API endpoint not working

- TikTok's API endpoints may change over time
- Check the latest documentation at https://developers.tiktok.com/doc/
- The `fetch_saved_videos()` function in `tiktok_official_api.py` may need updates based on current API structure

## Security Notes

- **Never share your Client Secret** publicly
- Keep `tiktok_access_token.json` private (it's already in `.gitignore`)
- Access tokens expire; the script will automatically refresh them when needed

## Alternative: Using Export JSON

If the official API setup is too complex or your app isn't approved yet, you can still use the export JSON method:

```powershell
python tiktok_collector.py
```

This uses the `user_data_tiktok.json` file you already have.

