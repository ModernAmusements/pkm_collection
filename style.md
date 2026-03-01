// Glass Colors
$glass-bg: rgba(255, 255, 255, 0.72);
$glass-bg-strong: rgba(255, 255, 255, 0.85);
$glass-border: rgba(255, 255, 255, 0.5);
$glass-shadow: rgba(0, 0, 0, 0.1);
$glass-highlight: rgba(255, 255, 255, 0.8);

// Liquid Glass Button/Icon Effect
$liquid-blur: 8px;
$liquid-saturation: 150%;
$liquid-bg: rgba(255, 255, 255, 0.6);
$liquid-bg-hover: rgba(255, 255, 255, 0.9);
$liquid-bg-active: rgba(0, 0, 0, 0.05);
$liquid-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.2), inset 1px 1.5px 0px -1px rgba(255, 255, 255, 0.8), inset -1px -1px 0px -1px rgba(255, 255, 255, 0.7), inset -1px -2px 1px -2px rgba(255, 255, 255, 0.5), inset 0.2px 0.5px 1px 0px rgba(0, 0, 0, 0.06), 0 2px 6px rgba(0, 0, 0, 0.1);
$liquid-shadow-hover: inset 0 0 0 1px rgba(255, 255, 255, 0.4), inset 1.5px 2px 0px -1.5px rgb(255, 255, 255), inset -1.5px -1.5px 0px -1.5px rgba(255, 255, 255, 0.9), inset -2px -3px 1px -2.5px rgba(255, 255, 255, 0.7), inset 0.3px 0.8px 1.5px 0px rgba(0, 0, 0, 0.08), 0 4px 12px rgba(0, 0, 0, 0.15);
$liquid-transition: all 200ms cubic-bezier(0.5, 0, 0, 1);
$liquid-scale-hover: scale(1.05);
$liquid-scale-active: scale(0.95);

// Button colors
$btn-primary-bg: rgba(0, 0, 0, 0.95);
$btn-success-bg: rgba(48, 209, 88, 0.8);
$btn-danger-bg: rgba(255, 69, 58, 0.8);
$btn-warning-bg: rgba(255, 159, 10, 0.8);

// Theme Variables (default - light)
:root {
  --c-glass: #bbbbbc;
  --c-light: #fff;
  --c-dark: #000;
  --c-content: #224;
  --c-bg: #e8e8e9;
  --glass-reflex-dark: 1;
  --glass-reflex-light: 1;
  --saturation: 150%;

  /* Liquid Glass Effect */
  --liquid-blur: 8px;
  --liquid-saturation: 150%;
  --liquid-bg: rgba(255, 255, 255, 0.6);
  --liquid-bg-hover: rgba(255, 255, 255, 0.9);
  --liquid-bg-active: rgba(0, 0, 0, 0.05);
  --liquid-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.2), inset 1px 1.5px 0px -1px rgba(255, 255, 255, 0.8), inset -1px -1px 0px -1px rgba(255, 255, 255, 0.7), inset -1px -2px 1px -2px rgba(255, 255, 255, 0.5), inset 0.2px 0.5px 1px 0px rgba(0, 0, 0, 0.06), 0 2px 6px rgba(0, 0, 0, 0.1);
  --liquid-shadow-hover: inset 0 0 0 1px rgba(255, 255, 255, 0.4), inset 1.5px 2px 0px -1.5px rgb(255, 255, 255), inset -1.5px -1.5px 0px -1.5px rgba(255, 255, 255, 0.9), inset -2px -3px 1px -2.5px rgba(255, 255, 255, 0.7), inset 0.3px 0.8px 1.5px 0px rgba(0, 0, 0, 0.08), 0 4px 12px rgba(0, 0, 0, 0.15);
  --liquid-transition: all 200ms cubic-bezier(0.5, 0, 0, 1);
  --liquid-scale-hover: scale(1.05);
  --liquid-scale-active: scale(0.95);

  /* Button colors */
  --btn-primary-bg: rgba(0, 0, 0, 0.8);
  --btn-primary-border: rgba(0, 0, 0, 1);
  --btn-success-bg: rgba(48, 209, 88, 0.8);
  --btn-success-border: rgba(48, 209, 88, 1);
  --btn-danger-bg: rgba(255, 69, 58, 0.8);
  --btn-danger-border: rgba(255, 69, 58, 1);
  --btn-warning-bg: rgba(255, 159, 10, 0.8);
  --btn-warning-border: rgba(255, 159, 10, 1);
}

// Dim Theme
body[data-theme="dim"] {
  --c-light: #99deff;
  --c-dark: #20001b;
  --c-glass: hsl(335 250% 74% / 1);
  --c-content: #d5dbe2;
  --c-action: #ff48a9;
  --c-bg: #152433;
  --glass-reflex-dark: 2;
  --glass-reflex-light: 0.7;
  --saturation: 200%;
}

// Dark Theme
body[data-theme="dark"] {
  --c-glass: #bbbbbc;
  --c-light: #fff;
  --c-dark: #000;
  --c-content: #e1e1e1;
  --c-action: #03d5ff;
  --c-bg: #1b1b1d;
  --glass-reflex-dark: 2;
  --glass-reflex-light: 0.3;
  --saturation: 150%;
}

// System Colors (Apple Tahoe)
$system-blue: #007AFF;
$system-green: #30D158;
$system-orange: #FF9F0A;
$system-red: #FF453A;
$system-purple: #BF5AF2;
$system-pink: #FF375F;
$system-yellow: #FFD60A;
$system-teal: #64D2FF;
$system-indigo: #5856D6;

// Border Radius (macOS Tahoe)
$radius-sm: 6px;
$radius-md: 10px;
$radius-lg: 15px;
$radius-xl: 22px;

// ==========================================================================
// 2. LEGACY VARIABLES (for backward compatibility)
// ==========================================================================

// Primary Colors
$color-primary: #007AFF;
$color-primary-hover: #0066CC;
$color-primary-active: #0055BB;
$color-primary-light: #E5F1FF;

// Secondary Colors
$color-secondary: #5856D6;
$color-secondary-hover: #4745B6;

// Accent Colors
$color-accent-green: #34C759;
$color-accent-red: #FF3B30;
$color-accent-orange: #FF9500;
$color-accent-purple: #AF52DE;
$color-accent-blue: #007AFF;

// Semantic Colors
$color-success: #30D158;
$color-warning: #FFD60A;
$color-error: #FF453A;
$color-info: #5856D6;

// Background Colors
$bg-primary: #F5F5F7;
$bg-secondary: #f5f5f5;
$bg-tertiary: #F0F0F2;
$bg-card: #FFFFFF;
$bg-overlay: rgba(0, 0, 0, 0.5);
$bg: #fff;

// Text Colors
$text-primary: #1D1D1F;
$text-secondary: #86868B;
$text-tertiary: #AEAEB2;
$text-inverse: #FFFFFF;
$text-link: #007AFF;
$color-text: #000;
$color-muted: #666;

// Border Colors
$border-light: #E5E5EA;
$border-default: #D2D2D7;
$border-dark: #C6C6C8;
$color-border: #000;
$border: 1px solid $color-border;

// Shadow Colors
$shadow-sm: rgba(0, 0, 0, 0.05);
$shadow-md: rgba(0, 0, 0, 0.1);
$shadow-lg: rgba(0, 0, 0, 0.15);
$shadow-xl: rgba(0, 0, 0, 0.2);

// Gradient Colors
$gradient-primary: linear-gradient(135deg, #007AFF 0%, #5856D6 100%);
$gradient-success: linear-gradient(135deg, #34C759 0%, #30D158 100%);
$gradient-warning: linear-gradient(135deg, #FF9500 0%, #FFD60A 100%);
$gradient-error: linear-gradient(135deg, #FF3B30 0%, #FF453A 100%);

// Font Families
$font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
$font-mono: 'SF Mono', 'Monaco', 'Menlo', 'Consolas', monospace;

// Spacing
$space-1: 4px;
$space-2: 8px;
$space-3: 12px;
$space-4: 16px;
$space-8: 32px;

// Typography
$text-xs: 11px;
$text-sm: 12px;
$text-base: 14px;
$text-lg: 16px;
$text-xl: 20px;
$text-2xl: 24px;
$text-3xl: 32px;
$text-4xl: 40px;

// Font Weights
$font-normal: 400;
$font-medium: 500;
$font-semibold: 600;
$font-bold: 700;

// Layout
$sidebar-width: 240px;
$header-height: 60px;

// Border Radius (macOS Tahoe)
$radius: 15px;

// Padding
$padding: 16px;

// ==========================================================================
// 2. MIXINS
// ==========================================================================

@mixin flex-center {
  display: flex;
  align-items: center;
  justify-content: center;
}

@mixin flex-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

@mixin flex-start {
  display: flex;
  align-items: center;
}

@mixin liquid-button($size: 32px) {
  width: $size;
  height: $size;
  padding: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: $liquid-bg;
  backdrop-filter: blur($liquid-blur) saturate($liquid-saturation);
  -webkit-backdrop-filter: blur($liquid-blur) saturate($liquid-saturation);
  cursor: pointer;
  box-shadow: $liquid-shadow;
  transition: $liquid-transition;

  &:hover {
    background: $liquid-bg-hover;
    transform: $liquid-scale-hover;
    box-shadow: $liquid-shadow-hover;
  }

  &:active {
    transform: $liquid-scale-active;
    background: $liquid-bg-active;
  }
}

@mixin card {
  border: $border;
  border-radius: $radius;
  padding: $padding;
}

@mixin scrollbar {
  overflow-x: auto;
  scrollbar-width: thin;
  scrollbar-color: #C7C7CC transparent;
  
  &::-webkit-scrollbar {
    height: 8px;
  }
  &::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.05);
    border-radius: 4px;
  }
  &::-webkit-scrollbar-thumb {
    background: #C7C7CC;
    border-radius: 4px;
  }
  &::-webkit-scrollbar-thumb:hover {
    background: #A0A0A4;
  }
}

@mixin scrollbar-webkit {
  @include scrollbar;
}

@mixin transition-height {
  transition: height 0.2s ease;
}

@mixin status-pill {
  display: inline-block;
  padding: $space-4 $space-8;
  border-radius: 50px;
  font-size: $text-4xl;
  font-weight: $font-bold;
  text-align: center;
  min-width: 280px;
}