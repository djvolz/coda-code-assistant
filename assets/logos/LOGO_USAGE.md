# Coda Logo Usage Guidelines

## Overview

The Coda logo represents a terminal window with AI capabilities, embodying our commitment to terminal-first AI development tools. The logo features a gradient header bar and terminal-style typography.

## Logo Files

### Available Formats

- **SVG** (`coda-terminal-logo.svg`) - Scalable vector format, preferred for web and documentation
- **PNG** - Raster format in multiple sizes:
  - `coda-terminal-logo-64x44.png` - Small icons
  - `coda-terminal-logo-128x89.png` - Medium icons
  - `coda-terminal-logo-256x179.png` - Large icons
  - `coda-terminal-logo-512x358.png` - High-res displays
  - `coda-terminal-logo-1024x716.png` - Marketing materials
- **ICO** (`coda-terminal-logo.ico`) - Favicon format

## Color Palette

- **Terminal Green**: `#00ff9d` - Primary brand color
- **Gradient Blue**: `#00bfff` - Header gradient midpoint
- **Purple**: `#9d00ff` - Header gradient endpoint
- **Background**: `#0d1117` - Terminal background
- **Text Gray**: `#888` - Terminal prompt

## Usage Guidelines

### Do's

- ✅ Use the SVG version when possible for best quality
- ✅ Maintain the aspect ratio (10:7) when resizing
- ✅ Ensure adequate contrast when placing on backgrounds
- ✅ Use the logo prominently in documentation headers
- ✅ Include the animated cursor effect in web implementations

### Don'ts

- ❌ Don't alter the colors or gradients
- ❌ Don't rotate or skew the logo
- ❌ Don't add effects like drop shadows or outlines
- ❌ Don't use the logo as a repeating pattern
- ❌ Don't place the logo on busy backgrounds

## Minimum Size

- Digital: 64px width minimum
- Print: 0.5 inch width minimum

## Clear Space

Maintain clear space around the logo equal to the height of the terminal header bar (approximately 1/7 of the total logo height).

## Implementation Examples

### Markdown
```markdown
![Coda Logo](assets/logos/coda-terminal-logo.svg)
```

### HTML
```html
<img src="assets/logos/coda-terminal-logo.svg" alt="Coda Terminal Logo" width="200">
```

### CSS Background
```css
.logo {
  background-image: url('assets/logos/coda-terminal-logo.svg');
  background-size: contain;
  background-repeat: no-repeat;
}
```

## Special Uses

### GitHub Social Preview
Use `coda-terminal-logo-1024x716.png` for repository social preview images.

### Favicon
Use `coda-terminal-logo.ico` for web application favicons.

### Documentation
Use the SVG version inline with a width of 200-400px depending on context.

## Questions?

For questions about logo usage, please refer to the main project documentation or open an issue in the repository.