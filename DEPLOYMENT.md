# Deployment Guide for Render.com

This guide will help you deploy your CSV to Shopify Converter application on Render.com.

## Prerequisites

1. A GitHub account
2. Your code pushed to a GitHub repository
3. A Render.com account (sign up at https://render.com - free tier available)

## Step-by-Step Deployment

### 1. Push Your Code to GitHub

If you haven't already, push your code to GitHub:

```bash
git init
git add .
git commit -m "Initial commit - Ready for Render deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

**Important**: Make sure the default template file `SomerSault_listings1_shopify_final_inventory-fixed.csv` is committed to your repository (it's now included in `.gitignore` exceptions).

### 2. Deploy on Render.com

1. **Sign in to Render**
   - Go to https://render.com
   - Sign up or log in with your GitHub account

2. **Create a New Web Service**
   - Click "New +" button
   - Select "Web Service"
   - Connect your GitHub account if not already connected
   - Select your repository

3. **Configure the Service**
   - **Name**: `csv-to-shopify-converter` (or any name you prefer)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`
   - **Plan**: Select "Free" (or upgrade if needed)

4. **Environment Variables** (Optional)
   - You can add environment variables if needed:
     - `FLASK_ENV=production` (already set in render.yaml)
     - `PYTHON_VERSION=3.11.0` (already set in render.yaml)

5. **Deploy**
   - Click "Create Web Service"
   - Render will automatically build and deploy your application
   - The first deployment may take 5-10 minutes

### 3. Access Your Application

- Once deployed, Render will provide you with a URL like:
  `https://csv-to-shopify-converter.onrender.com`
- Your app will be live and accessible at this URL!

## Files Created for Deployment

- **Procfile**: Tells Render how to run your application
- **render.yaml**: Optional configuration file for Render
- **Updated requirements.txt**: Now includes `gunicorn` for production server
- **Updated app.py**: Now uses `PORT` environment variable and production settings

## Important Notes

1. **Free Tier Limitations**:
   - Render free tier spins down after 15 minutes of inactivity
   - First request after spin-down may take 30-60 seconds
   - Consider upgrading to paid plan for always-on service

2. **File Uploads**:
   - Files are stored in temporary directories
   - Files are cleaned up automatically
   - Maximum file size: 50MB (configured in app.py)

3. **Template File**:
   - The default template `SomerSault_listings1_shopify_final_inventory-fixed.csv` must be in your repository
   - Users can also upload their own template files

## Troubleshooting

### Build Fails
- Check that all dependencies are in `requirements.txt`
- Verify Python version compatibility
- Check Render build logs for specific errors

### Application Crashes
- Check Render logs in the dashboard
- Verify that `Procfile` is correct
- Ensure `gunicorn` is in `requirements.txt`

### 502 Bad Gateway
- This usually means the app is spinning up (free tier)
- Wait 30-60 seconds and try again
- Check Render logs for errors

### Template File Not Found
- Ensure `SomerSault_listings1_shopify_final_inventory-fixed.csv` is committed to your repository
- Check that it's not being ignored by `.gitignore`

## Updating Your Application

1. Make changes to your code
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Your update message"
   git push
   ```
3. Render will automatically detect the changes and redeploy
4. Monitor the deployment in Render dashboard

## Custom Domain (Optional)

1. Go to your service settings in Render
2. Click "Custom Domains"
3. Add your domain
4. Follow DNS configuration instructions

---

**Your app is now live! 🎉**

