# Coda Logo Usage Guidelines

## Overview

The Coda logo represents a terminal window with AI capabilities, embodying our commitment to terminal-first AI development tools. The logo features a gradient header bar and terminal-style typography.

## Logo Variants

### 1. Main Logo
Full terminal window with command prompt and "AI ready" text.
- **SVG**: `coda-terminal-logo.svg`
- **PNG**: `coda-terminal-logo-{size}x{height}.png`
- **Sizes**: 64x44, 128x89, 256x179, 512x358, 1024x716
- **Use cases**: README headers, documentation, marketing materials

### 2. Compact Logo
Smaller terminal window with just the command prompt.
- **SVG**: `coda-terminal-logo-compact.svg`
- **PNG**: `coda-terminal-logo-compact-{size}x{height}.png`
- **Sizes**: 64x48, 128x96, 256x192, 512x384
- **Use cases**: Smaller spaces, inline documentation, badges

### 3. Icon Logo
Square terminal window with large "C" letter.
- **SVG**: `coda-terminal-logo-icon.svg`
- **PNG**: `coda-terminal-logo-icon-{size}x{size}.png`
- **Sizes**: 16x16, 32x32, 48x48, 64x64, 128x128, 256x256, 512x512
- **Use cases**: App icons, favicons, avatar images

### Additional Files
- **ICO**: `coda-terminal-logo.ico` - Multi-resolution favicon (16x16 to 64x64)

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
<!-- Main logo for headers -->
![Coda Logo](assets/logos/coda-terminal-logo.svg)

<!-- Compact logo for inline use -->
![Coda](assets/logos/coda-terminal-logo-compact.svg)

<!-- Icon for small spaces -->
![Coda Icon](assets/logos/coda-terminal-logo-icon.svg)
```

### HTML
```html
<!-- Main logo -->
<img src="assets/logos/coda-terminal-logo.svg" alt="Coda Terminal Logo" width="400">

<!-- Compact logo -->
<img src="assets/logos/coda-terminal-logo-compact.svg" alt="Coda Compact Logo" width="120">

<!-- Icon -->
<img src="assets/logos/coda-terminal-logo-icon.svg" alt="Coda Icon" width="80">
```

### CSS Background
```css
/* Main logo */
.logo-main {
  background-image: url('assets/logos/coda-terminal-logo.svg');
  width: 200px;
  height: 140px;
}

/* Compact logo */
.logo-compact {
  background-image: url('assets/logos/coda-terminal-logo-compact.svg');
  width: 120px;
  height: 90px;
}

/* Icon */
.logo-icon {
  background-image: url('assets/logos/coda-terminal-logo-icon.svg');
  width: 80px;
  height: 80px;
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