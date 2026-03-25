# ReadWise LinkedIn Launch Kit

This folder implements your client-focused LinkedIn launch plan for US/Canada/Dubai outreach.

## Files

- `caption.txt`: Final post caption with `[YOUR_RENDER_URL]` placeholder.
- `first_comment.txt`: First comment to post immediately after publishing.
- `carousel_slides.md`: Exact 6-slide copy and design-ready notes.
- `featured_section.md`: Text and links to add in LinkedIn Featured.
- `project_entry.md`: Text for LinkedIn Projects section.
- `pre_publish_checklist.md`: Execution steps and quality checks.
- `engagement_tracker.csv`: 72-hour tracking template.
- `validate_links.ps1`: Quick link health check for demo + GitHub URLs.
- `finalize_linkedin_assets.ps1`: Replaces `[YOUR_RENDER_URL]` in all assets and validates links.
- `implementation_status.md`: What is already done vs what stays manual on LinkedIn.

## Quick Use

1. Finalize all assets with your live demo URL:

```powershell
powershell -ExecutionPolicy Bypass -File .\linkedin\finalize_linkedin_assets.ps1 -DemoUrl "https://your-service-name.onrender.com"
```

2. Build the 6-slide carousel using `carousel_slides.md`.
3. (Optional re-check) Run `validate_links.ps1` directly:

```powershell
powershell -ExecutionPolicy Bypass -File .\linkedin\validate_links.ps1 -DemoUrl "https://your-service-name.onrender.com"
```

4. Publish on **Thursday, February 26, 2026 at 10:00 AM Eastern Time**.
5. Post `first_comment.txt` immediately after publishing.
6. Track results in `engagement_tracker.csv` for the first 72 hours.
