# Frequently Asked Questions (FAQ)

## 🎯 General Questions

### Q: What is this portfolio?
**A:** This is an interactive web-based operating system UI portfolio that showcases Harshith Gangaraju's skills in cybersecurity, programming, and web development. It's both a portfolio and a proof of concept for advanced front-end development.

### Q: Can I use this as a template for my portfolio?
**A:** Yes! This project is MIT licensed. Feel free to fork it, modify it, and use it as your own portfolio. Just maintain the license file.

### Q: Is this a real operating system?
**A:** No, it's a web-based simulation/UI that mimics an OS interface. All commands are simulated for portfolio purposes.

---

## 🖥️ Usage Questions

### Q: How do I open the portfolio?
**A:** Simply download or clone the repository and open `harshith-os.html` in any modern web browser. No server required!

### Q: What are the keyboard shortcuts?
**A:** 
- `↑` / `↓` arrows in terminal: Navigate command history
- `Tab`: Prevented (reserved for compatibility)
- Konami Code: `↑↑↓↓←→←→BA` = Activate God Mode (green theme)

### Q: Can I use this on mobile?
**A:** Yes! The portfolio is fully responsive. All features work on phones and tablets.

### Q: Why doesn't the boot screen show twice?
**A:** The `sessionStorage` remembers that you've booted once. It's removed automatically on browser cache clear or `reboot` command.

---

## 💻 Terminal Commands

### Q: What terminal commands are available?
**A:** See the [Getting Started Guide](./GETTING_STARTED.md#terminal-commands) for the complete list.

### Q: Can I add my own commands?
**A:** Yes! Edit the `handleCommand()` function in `harshith-os.html` to add custom commands.

### Q: Why does "hack nasa" just simulate?
**A:** It's a simulated hacking sequence for portfolio demonstration. No actual hacking occurs (that would be illegal 😄).

### Q: What happens if I run `reboot`?
**A:** The page refreshes and the boot sequence plays again.

---

## 🎨 Themes & Appearance

### Q: How many themes are there?
**A:** 3 built-in themes: Red (default), Green, and Blue. Use `theme [color]` to switch.

### Q: What's the Konami code?
**A:** A classic video game easter egg. Press `↑↑↓↓←→←→BA` (when NOT in terminal input) to activate "God Mode" with the green theme.

### Q: Can I customize colors?
**A:** Yes! Edit the CSS variables in the `<style>` section:
```css
:root {
    --neon-color: #ff003c;  /* Change this */
    --neon-dim: #80001e;    /* And this */
    /* ... */
}
```

### Q: Why is the matrix background so faint?
**A:** It's designed that way for subtlety. You can increase the opacity in the CSS.

---

## 🎵 Sound & Performance

### Q: Why is there no sound?
**A:** Browsers restrict audio by default. Interact with the page first (click something), then sounds should work.

### Q: Can I disable sounds?
**A:** Modify the `playSound()` function to have it do nothing, or comment out calls to `playSound()`.

### Q: The animation is laggy on my device
**A:** 
- Disable hardware acceleration in browser settings
- Reduce visual effects (matrix effect, scanlines)
- Try a different browser
- Close other applications

### Q: What's the performance impact?
**A:** Minimal! No external dependencies, lightweight CSS animations, and optimized JavaScript. Runs smoothly even on older devices.

---

## 🔧 Technical Questions

### Q: What's the tech stack?
**A:** Pure HTML5, CSS3, and Vanilla JavaScript. No frameworks or dependencies!

### Q: Can I host this on GitHub Pages?
**A:** Yes! Just enable GitHub Pages in your repository settings and point it to the `main` branch.

### Q: Is the code obfuscated?
**A:** No! The code is clean, commented, and easy to understand. Perfect for learning.

### Q: Can I modify the source code?
**A:** Absolutely! The HTML file is completely yours to modify. Feel free to add features, change styling, or rewrite sections.

---

## 🐛 Troubleshooting

### Q: Windows won't drag on desktop
**A:** Dragging is disabled on mobile devices for better UX. It only works on desktop browsers.

### Q: My browser shows an error in the console
**A:** 
- This is usually harmless (often related to extensions)
- Try clearing cache and reloading
- If it persists, open an issue on GitHub

### Q: The page takes forever to load
**A:** 
- Check your internet connection (it loads Google Fonts)
- Try a hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
- Disable browser extensions temporarily

### Q: Some windows overlap badly
**A:** Minimize a window, then reopen it. It should reposition automatically.

### Q: The terminal input isn't responding
**A:** 
- Click anywhere in the terminal window to ensure focus
- Try pressing `Enter` on an empty line
- Refresh the page if it persists

---

## 📱 Mobile-Specific Questions

### Q: Is there a mobile app?
**A:** No, but this website is mobile-optimized and works great in mobile browsers. You can also add it to your home screen for app-like experience.

### Q: Why can't I drag windows on mobile?
**A:** Dragging is disabled on touch devices for better usability. Windows auto-position themselves when opened.

### Q: Can I use all features on mobile?
**A:** Yes! All terminal commands, themes, and windows work on mobile. The experience is optimized for smaller screens.

---

## 🤝 Contributing & Support

### Q: How can I contribute?
**A:** See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines on submitting issues and pull requests.

### Q: How do I report a bug?
**A:** Open an issue on GitHub with:
- Description of the bug
- Steps to reproduce
- Your browser and OS
- Screenshots (if helpful)

### Q: Can I suggest new features?
**A:** Yes! Open a GitHub issue or reach out directly at harshith6754@gmail.com

### Q: Is this project maintained?
**A:** Yes! Active development and improvements are ongoing.

---

## 📄 License & Legal

### Q: Can I use this commercially?
**A:** Yes, under the MIT License. You can use it for commercial projects.

### Q: Do I need to give credit?
**A:** Not legally required (MIT License), but it's appreciated! A link back is nice 🙂

### Q: What about the terminal simulation - is it legal?
**A:** Yes! It's completely simulated for educational/portfolio purposes. No actual hacking occurs.

---

## 🎓 Learning Questions

### Q: Can I learn web development from this code?
**A:** Absolutely! It demonstrates:
- Advanced HTML5/CSS3
- JavaScript event handling
- Canvas API
- Web Audio API
- Responsive design
- CSS animations

### Q: Can students use this for projects?
**A:** Yes, but add your own customizations and make it your own. Original work is always preferred.

### Q: Are there comments in the code?
**A:** Yes, the JavaScript is well-commented for learning purposes.

---

## 🆘 Still Have Questions?

- 📧 Email: harshith6754@gmail.com
- 💼 LinkedIn: [Harshith Gangaraju](https://www.linkedin.com/in/harshith-gangaraju-09a69638b)
- 🐙 GitHub Issues: [Open an issue](https://github.com/hotaro6754/hotaro6754/issues)

---

**Last Updated**: November 24, 2025
