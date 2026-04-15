#!/usr/bin/env python3
"""
Generate a simple icon for RegearApp using PIL (Pillow)
This creates a basic 256x256 PNG icon that can be converted to ICO later
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    
    # Create image with gradient background
    img = Image.new('RGB', (256, 256), color=(45, 135, 207))  # Blue background
    draw = ImageDraw.Draw(img)
    
    # Draw a simple gear/cog shape to represent "Regear"
    # Center circle
    draw.ellipse([60, 60, 196, 196], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    
    # Inner circle
    draw.ellipse([90, 90, 166, 166], fill=(45, 135, 207), outline=(255, 255, 255), width=2)
    
    # Gear teeth (simplified)
    tooth_positions = [
        (128, 40),   # Top
        (188, 68),   # Top-right
        (216, 128),  # Right
        (188, 188),  # Bottom-right
        (128, 216),  # Bottom
        (68, 188),   # Bottom-left
        (40, 128),   # Left
        (68, 68),    # Top-left
    ]
    
    for x, y in tooth_positions:
        draw.polygon([(x, y), (x-8, y-8), (x+8, y-8)], fill=(255, 255, 255))
    
    # Save as PNG first (easier than ICO)
    img.save('icon.png', 'PNG')
    print("✓ icon.png created successfully")
    
    # Try to convert to ICO if pillow supports it
    try:
        img.save('icon.ico', 'ICO')
        print("✓ icon.ico created successfully")
    except Exception as e:
        print(f"Note: Could not create ICO directly. You can convert PNG to ICO online.")
        print(f"  Error: {e}")
    
except ImportError:
    print("PIL not available. Creating a minimal placeholder icon...")
    # Fallback: Create a minimal valid ICO file
    # This is a 1x1 transparent ICO file (minimal valid format)
    ico_data = (
        b'\x00\x00\x01\x00\x01\x00 \x20\x00\x00\x01\x00\x20\x00'
        b'\x28\x00\x00\x00\x20\x00\x00\x00\x40\x00\x00\x00\x01'
        b'\x00\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
    )
    with open('icon.ico', 'wb') as f:
        f.write(ico_data)
    print("✓ Minimal placeholder icon.ico created")
