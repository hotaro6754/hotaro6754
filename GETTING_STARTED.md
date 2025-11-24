# 📖 Getting Started

## Quick Start

### Option 1: View Online (Easiest)
1. Visit your GitHub repository
2. Click on `harshith-os.html`
3. Click "View Raw" and then refresh to see the rendered HTML

Or open directly in browser: `file:///path/to/harshith-os.html`

### Option 2: Clone & Run Locally

```bash
# Clone the repository
git clone https://github.com/hotaro6754/hotaro6754.git
cd hotaro6754

# Open in your default browser
# macOS
open harshith-os.html

# Linux
xdg-open harshith-os.html

# Windows
start harshith-os.html
```

### Option 3: Local Web Server (Recommended)

```bash
# Using Python 3
python -m http.server 8000

# Using Node.js (if installed)
npx http-server

# Then visit: http://localhost:8000/harshith-os.html
```

---

## 🎮 How to Use the Portfolio

### Boot Sequence
- The system starts with an animated boot sequence (skipped on subsequent visits)
- View the boot logs as they appear
- Desktop loads automatically

### Navigation
- **Click desktop icons** to open windows
- **Drag window headers** to move windows around
- **Click minimize/maximize/close buttons** to manage windows

### Terminal Commands

```bash
# Display available commands
help

# Open windows via terminal
open about
open skills
open projects
open certs
open ctf
open contact

# View the full project roadmap
cat roadmap.txt

# Switch themes
theme red
theme green
theme blue

# View user information
whoami

# Show current date/time
date

# Simulate hacking sequence
hack google.com
hack nasa

# Clear terminal output
clear

# Restart the system
reboot
```

### Easter Eggs

1. **Konami Code**: While NOT in the terminal input, press:
   - ⬆️ ⬆️ ⬇️ ⬇️ ⬅️ ➡️ ⬅️ ➡️ B A
   - This activates "GOD MODE" with a special green theme!

2. **Hidden Flag**: Run `cat .hidden_flag` in the terminal

---

## 🎨 Themes

Switch between three color schemes:

### Red Theme (Default)
- Neon Color: `#ff003c`
- Professional and bold

### Green Theme
- Neon Color: `#00ff41`
- Matrix-inspired
- Activated via Konami code

### Blue Theme
- Neon Color: `#00e5ff`
- Modern and sleek

---

## 📱 Mobile Compatibility

- ✅ Fully responsive design
- ✅ Touch-friendly interface
- ✅ Optimized window sizing for mobile
- ✅ All features work on tablets

---

## 🖥️ Browser Support

| Browser | Status | Notes |
|---------|--------|-------|
| Chrome | ✅ Full Support | Recommended |
| Firefox | ✅ Full Support | Excellent |
| Safari | ✅ Full Support | macOS & iOS |
| Edge | ✅ Full Support | Windows |
| Opera | ✅ Full Support | - |
| IE 11 | ❌ Not Supported | Use modern browser |

---

## ⚙️ Technical Details

### Technologies Used
- **HTML5**: Semantic markup
- **CSS3**: Advanced styling, animations, grid layout
- **Vanilla JavaScript**: No frameworks or dependencies
- **Canvas API**: Matrix rain background
- **Web Audio API**: Sound effects
- **Font Awesome**: Icons

### Features
- 🎬 Boot animation with typewriter effect
- 🎨 Dynamic theme system with CSS variables
- 🪟 Complete window management (drag, minimize, maximize, close)
- 📝 Terminal with command history and auto-complete
- 🎵 Sound effects for user interactions
- 📊 Progress bars and animations
- 🌧️ Matrix rain background effect
- 🎯 Responsive grid layout

### Performance
- Zero external JavaScript dependencies
- Lightweight CSS (~800 lines)
- Optimized animations using CSS transforms
- Efficient DOM manipulation

---

## 🐛 Troubleshooting

### Sound not working?
- Check browser volume settings
- Ensure Web Audio API is enabled
- Reload the page

### Windows not dragging?
- Works on desktop only (disabled on mobile)
- Try on a different browser
- Clear browser cache and reload

### Matrix effect not visible?
- It's subtle by design (opacity: 0.15)
- Check if browser hardware acceleration is enabled
- Try adjusting background brightness

### Themes not switching?
- Make sure you type the complete theme name (red/green/blue)
- Clear browser cache if changes don't apply
- Refresh the page

---

## 📝 Notes

- This portfolio uses `sessionStorage` to remember if boot sequence was shown
- All data is local - no server communication
- Windows positions are reset on page refresh
- Terminal history is cleared on page reload

---

## 🎓 Learning Resources

This portfolio demonstrates:
- ✨ Advanced HTML5/CSS3 concepts
- 🎬 JavaScript event handling & animation
- 🖼️ Canvas API for graphics
- 🔊 Web Audio API for sound
- 📐 Responsive web design
- 🎨 CSS custom properties (variables)
- 🖱️ Drag-and-drop functionality
- 🎯 Window management system

---

Need help? Check the [FAQ](./FAQ.md) or open an issue!
