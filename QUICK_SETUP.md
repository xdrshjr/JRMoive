# Quick Setup Instructions

## Backend Setup (if not already running)

```bash
# Terminal 1: Start Backend
cd backend
pip install -r requirements.txt
cp env.example .env
# Edit .env with your API keys
python run_dev.py
# Backend should be running on http://localhost:8000
```

## Frontend Setup

```bash
# Terminal 2: Start Frontend
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local
# Edit .env.local if backend is not on localhost:8000

# Start development server
npm run dev

# Open browser to http://localhost:3000
```

## Verify Setup

1. **Check Backend Health:**
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status":"healthy",...}`

2. **Check Frontend:**
   Open http://localhost:3000 in your browser
   You should see the "AI Movie Generator" header

## Usage Flow

1. **Step 1:** Enter script description → Click "Polish Script" → Edit if needed → Next
2. **Step 2:** Generate or upload character images → Select best images → Next
3. **Step 3:** Generate or upload scene images → Select best images → Next
4. **Step 4:** Monitor video generation progress → Wait for completion
5. **Step 5:** Preview video → Download → Create another or exit

## Troubleshooting

### Backend Connection Failed
- Ensure backend is running: `curl http://localhost:8000/health`
- Check `.env.local` has correct `NEXT_PUBLIC_API_BASE_URL`
- Check browser console for CORS errors

### Images Not Loading
- Check `next.config.js` has correct image domains
- Verify image URLs are accessible
- Check browser network tab for failed requests

### Build Errors
```bash
cd frontend
rm -rf .next node_modules
npm install
npm run dev
```

## Production Deployment

```bash
cd frontend
npm run build
npm start
# Frontend runs on http://localhost:3000
```

## Environment Variables

### Backend (.env)
```bash
FAST_LLM_API_KEY=your_key
DOUBAO_API_KEY=your_key
VEO3_API_KEY=your_key
# See backend/env.example for full list
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_LOG_LEVEL=info
```

## API Keys Required

You need API keys for:
- **LLM Service** (for script polishing)
- **Image Service** (Doubao/NanoBanana for images)
- **Video Service** (Veo3 for video generation)

See `backend/docs/README.md` for how to obtain these keys.

## Support

- Frontend Docs: `frontend/README.md`
- API Integration: `frontend/API_INTEGRATION.md`
- Backend Docs: `backend/docs/README.md`
- Implementation Details: `frontend/IMPLEMENTATION_SUMMARY.md`

