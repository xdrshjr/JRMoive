# AI Movie Generator - Frontend

Modern, elegant Next.js + React frontend for AI movie generation with Apple-inspired design.

## Features

✨ **5-Step Workflow**
- Script Input & Polish - AI-powered script enhancement
- Character Images - Generate or upload character reference images
- Scene Images - Generate or upload scene reference images
- Video Generation - Real-time progress monitoring with logs
- Result Preview - Download and preview your generated video

🎨 **Apple-Inspired Design**
- Clean, minimal interface
- Smooth transitions and animations
- Responsive design (mobile-friendly)
- Light and dark mode support
- San Francisco font family

🔧 **Technology Stack**
- Next.js 14+ (App Router)
- React 18+
- TypeScript (strict mode)
- Tailwind CSS
- RESTful API integration

## Quick Start

### Prerequisites

- Node.js 18.0 or higher
- npm 9.0 or higher
- Backend API running on `http://localhost:8000`

### Installation

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Configure environment:**
   ```bash
   cp .env.local.example .env.local
   ```
   
   Edit `.env.local` to match your backend URL:
   ```bash
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
   NEXT_PUBLIC_LOG_LEVEL=info
   ```

4. **Run development server:**
   ```bash
   npm run dev
   ```

5. **Open browser:**
   Navigate to [http://localhost:3000](http://localhost:3000)

### Production Build

```bash
npm run build
npm start
```

## Project Structure

```
frontend/
├── src/
│   ├── app/                     # Next.js App Router
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Main page with workflow
│   │   └── globals.css         # Global styles
│   ├── components/
│   │   ├── Header.tsx          # Header component
│   │   ├── StepContainer.tsx   # Step workflow wrapper
│   │   ├── steps/              # Step components (1-5)
│   │   │   ├── Step1ScriptInput.tsx
│   │   │   ├── Step2CharacterImages.tsx
│   │   │   ├── Step3SceneImages.tsx
│   │   │   ├── Step4VideoProgress.tsx
│   │   │   └── Step5ResultPreview.tsx
│   │   └── ui/                 # Reusable UI components
│   │       ├── Button.tsx
│   │       ├── Input.tsx
│   │       ├── Textarea.tsx
│   │       ├── Card.tsx
│   │       ├── ProgressBar.tsx
│   │       ├── ImageGrid.tsx
│   │       ├── LogViewer.tsx
│   │       └── LoadingAnimation.tsx
│   ├── lib/
│   │   ├── api.ts              # API client
│   │   ├── logger.ts           # Logging utility
│   │   └── types.ts            # TypeScript types
│   └── styles/
│       └── apple-theme.css     # Apple design tokens
├── public/                      # Static assets
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.js
```

## Usage Guide

### Step 1: Script Input & Polish

1. Enter your script description or outline
2. Click "Polish Script" to use AI enhancement
3. Edit the polished script as needed
4. Click "Next" to proceed

### Step 2: Character Images

1. The system extracts characters from your script
2. For each character:
   - Choose "Auto Generate" or "Manual Upload"
   - Set number of images (1-5) if auto-generating
   - Generate or upload images
   - Select your preferred image
3. Click "Next" when all characters have images

### Step 3: Scene Images

1. The system extracts scenes from your script
2. For each scene:
   - Choose "Auto Generate" or "Manual Upload"
   - Set number of images (1-5) if auto-generating
   - Generate or upload scene images
   - Select your preferred image
3. Click "Next" to start video generation

### Step 4: Video Generation

1. Monitor real-time progress (0-100%)
2. View generation stages
3. Check logs for detailed information
4. Cancel if needed

### Step 5: Result Preview

1. Preview your generated video
2. View video metadata
3. Download the video
4. Create another video or exit

## API Integration

The frontend communicates with the FastAPI backend using RESTful APIs:

### Current Endpoints Used

- `POST /api/v1/llm/chat` - Script polishing
- `POST /api/v1/images/generate` - Image generation
- `POST /api/v1/videos/generate` - Video generation
- `GET /api/v1/tasks/{task_id}` - Task status polling
- `DELETE /api/v1/tasks/{task_id}` - Cancel task

### Future Endpoints (TODO)

See [API_INTEGRATION.md](./API_INTEGRATION.md) for details on planned backend endpoints.

## Configuration

### Environment Variables

```bash
# Backend API URL
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Polling configuration
NEXT_PUBLIC_POLL_INTERVAL_MS=2000
NEXT_PUBLIC_POLL_MAX_INTERVAL_MS=10000

# Log level (debug, info, warn, error)
NEXT_PUBLIC_LOG_LEVEL=info

# Debug mode
NEXT_PUBLIC_DEBUG=false
```

### Design Customization

Modify colors and design tokens in `tailwind.config.ts`:

```typescript
colors: {
  apple: {
    blue: '#007AFF',    // Primary color
    green: '#34C759',   // Success color
    // ... more colors
  }
}
```

## Development

### Scripts

```bash
npm run dev        # Start development server
npm run build      # Build for production
npm run start      # Start production server
npm run lint       # Run ESLint
npm run type-check # TypeScript type checking
```

### Code Style

- TypeScript strict mode enabled
- ESLint for code quality
- Prettier for formatting (recommended)
- Component files use PascalCase
- Utility files use camelCase

### Logging

The frontend includes a comprehensive logging system:

```typescript
import { logger } from '@/lib/logger';

logger.info('Component', 'User action performed', { data });
logger.debug('Component', 'Debug information', { details });
logger.warn('Component', 'Warning message', { context });
logger.error('Component', 'Error occurred', error);
```

## Troubleshooting

### Backend Connection Issues

If you see "Network Error" or "API Error":

1. Ensure backend is running on `http://localhost:8000`
2. Check `NEXT_PUBLIC_API_BASE_URL` in `.env.local`
3. Verify backend CORS is enabled
4. Check browser console for errors

### Image Loading Issues

If images don't display:

1. Check Next.js image domains in `next.config.js`
2. Add your image service domains to `images.domains`
3. Ensure image URLs are accessible

### Build Errors

If build fails:

1. Run `npm run type-check` to find TypeScript errors
2. Clear `.next` folder: `rm -rf .next`
3. Reinstall dependencies: `rm -rf node_modules && npm install`

## Performance

- **First Load JS**: ~200KB (gzipped)
- **Route Loading**: Instant with App Router
- **Image Optimization**: Automatic with Next.js Image
- **Code Splitting**: Automatic per route

## Browser Support

- Chrome/Edge: Last 2 versions
- Firefox: Last 2 versions
- Safari: Last 2 versions
- Mobile browsers: iOS 12+, Android 8+

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
- Check the [API Integration Guide](./API_INTEGRATION.md)
- Review browser console logs
- Check backend API logs
- Create an issue in the repository

## Roadmap

- [ ] WebSocket support for real-time updates
- [ ] Dark mode toggle
- [ ] Multi-language support
- [ ] Advanced video editing options
- [ ] Project save/load functionality
- [ ] User authentication
- [ ] Video preview thumbnails
- [ ] Batch processing

## Credits

Built with ❤️ using Next.js, React, and Tailwind CSS.
Design inspired by Apple's Human Interface Guidelines.

