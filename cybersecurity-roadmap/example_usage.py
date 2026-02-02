#!/usr/bin/env python3
"""
Simple example script demonstrating how to use the roadmap generator
"""

from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from roadmap_generator import RoadmapGenerator


def main():
    """Generate the roadmap with custom options"""
    
    print("🎯 Cybersecurity Roadmap Generator Example")
    print("=" * 50)
    print()
    
    # Create generator
    generator = RoadmapGenerator(output_dir="output")
    
    # Generate with custom filename
    output_file = generator.generate(filename="my_cybersecurity_roadmap.pdf")
    
    print()
    print("✅ Success!")
    print(f"📄 Your roadmap: {output_file}")
    print()
    print("Next steps:")
    print("  1. Open the PDF in your favorite PDF reader")
    print("  2. Scan QR codes to access resources quickly")
    print("  3. Follow the stage progression at your own pace")
    print("  4. Track your progress through the stages")
    print()
    print("Happy learning! 🚀")


if __name__ == "__main__":
    main()
