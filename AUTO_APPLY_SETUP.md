# Auto-Apply Setup Guide

## Overview
The Auto-Apply feature uses AI-powered browser automation to automatically fill job application forms. It **does NOT submit** the application - the user must review and submit manually.

## Prerequisites

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
playwright install chromium
```

### 2. Environment Variables
Ensure these are set in your `.env` file:
```env
GEMINI_API_KEY=your_gemini_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

## How It Works

### Backend (Python + Playwright + LLM)
1. **Browser Launch**: Opens a **visible** Chromium browser window
2. **Navigation**: Goes to the job URL
3. **Form Detection**: Uses Gemini LLM to identify form fields
4. **Auto-Fill**: Fills fields with user profile data (name, email, phone, skills, etc.)
5. **Resume Upload**: Uploads resume file if available
6. **Stop Before Submit**: Does NOT click the final submit button
7. **User Review**: Browser stays open for user to review and submit

### Frontend (Next.js/React)
- Fetches user profile data from Supabase
- Calls `/agent4/auto-apply` endpoint
- Shows real-time status updates
- Displays success/error messages

## User Profile Data Fields

The following fields are automatically extracted and filled:
- **Basic**: name, email, first_name, last_name
- **Contact**: phone, mobile
- **Location**: location, city
- **Links**: linkedin_url, github_url, portfolio_url
- **Skills**: skills (comma-separated), technologies
- **Experience**: years_of_experience, current_role, current_company

## Usage

### From Frontend
1. Navigate to `/jobs/[id]/apply`
2. Click "Auto-Apply (Beta)" button
3. Wait for browser to open and fill form
4. Review filled information in browser
5. Click submit manually

### API Endpoint
```typescript
POST /agent4/auto-apply
{
  "job_url": "https://example.com/apply",
  "user_data": {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "linkedin": "https://linkedin.com/in/johndoe",
    "skills": "Python, React, Node.js"
  },
  "user_id": "uuid", // Optional: to fetch resume from Supabase
  "resume_path": "/path/to/resume.pdf", // Optional: local file
  "resume_url": "https://..." // Optional: remote file
}
```

## Troubleshooting

### Browser doesn't open
- Check if Playwright Chromium is installed: `playwright install chromium`
- Check if `browser-use>=0.11.0` is installed: `pip show browser-use`

### Form fields not filled
- Check browser console for LLM errors
- Ensure Gemini API key is valid
- Check if the job site has anti-bot protection (CAPTCHA)

### Resume not uploaded
- Verify resume exists in Supabase storage as `{user_id}.pdf` or `{user_id}.docx`
- Check file permissions
- Try providing `resume_url` instead

### Login/Authentication Required
- Some job sites require login before applying
- Auto-apply will detect this and report the error
- User must login manually first

## Limitations

1. **No Submit**: Feature intentionally does NOT submit - user must review
2. **CAPTCHAs**: Cannot bypass CAPTCHA challenges
3. **Login Required**: Cannot auto-login to job sites
4. **Complex Forms**: Some multi-step/dynamic forms may not work
5. **Site-Specific**: Each job site has different form structure

## Best Practices

1. **Always Review**: Check all filled fields before submitting
2. **Complete Profile**: Fill all fields in user profile for better results
3. **Resume Ready**: Upload resume to Supabase storage beforehand
4. **One at a Time**: Run one auto-apply at a time (browser resource)
5. **Manual Fallback**: Be ready to fill manually if auto-fill fails

## Architecture

```
Frontend (Next.js)
  ↓ POST /agent4/auto-apply
Backend (FastAPI)
  ↓ calls run_auto_apply()
Browser-Use + Playwright
  ↓ launches Chromium
Gemini LLM
  ↓ generates browser actions
Form Auto-Filled
  ↓ user reviews
Manual Submit
```

## Supported Job Sources

Works with jobs from any source:
- ✅ LinkedIn (if not requiring login)
- ✅ Indeed  
- ✅ Greenhouse
- ✅ Lever
- ✅ Company career pages
- ✅ Jobs from SERP API
- ✅ Jobs from JSearch API
- ✅ Jobs from Mantiks API

## Security Notes

- Browser runs with `disable_security: True` to allow file uploads
- Browser is **visible** (not headless) for transparency
- No credentials are stored or used for auto-login
- Resume files are downloaded temporarily and cleaned up

## Future Enhancements

- [ ] Multi-step form support
- [ ] Smart retry on errors
- [ ] Form validation before user review
- [ ] Application tracking/history
- [ ] Support for cover letter upload
- [ ] Video question detection

## Support

If auto-apply fails:
1. Check backend logs: `uvicorn main:app --reload --port 8000`
2. Check browser console in the opened window
3. Try manual application
4. Report issues with job URL and error message
