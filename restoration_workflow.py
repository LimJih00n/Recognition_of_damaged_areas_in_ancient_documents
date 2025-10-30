#!/usr/bin/env python3
"""
Integrated Restoration Workflow
조선시대 문서 복원 통합 워크플로우

전체 과정을 한 번에 실행:
1. 구멍 검출 (extract_whiteness_based.py)
2. 레이저 커팅 레이아웃 생성 (create_cutting_layout.py)
3. 복원 가이드 생성 (create_restoration_guide.py)

사용법:
  python restoration_workflow.py --input document.tif --output-dir results/document
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
import time


def run_command(cmd: list, step_name: str) -> bool:
    """명령어 실행 및 에러 처리"""
    print(f"\n{'='*60}")
    print(f"Step: {step_name}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print()

    try:
        result = subprocess.run(cmd, check=True, capture_output=False, text=True)
        print(f"\n[OK] {step_name} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Error in {step_name}:")
        print(f"  Return code: {e.returncode}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected error in {step_name}:")
        print(f"  {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Integrated restoration workflow - hole detection, cutting layout, and restoration guide',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single document
  python restoration_workflow.py --input datasets/test_small.jpg --output-dir results/test

  # Process with custom parameters
  python restoration_workflow.py --input datasets/1첩/w_0001.tif --output-dir results/w_0001 --paper-size A3 --min-area 100

  # Skip hole detection if already done
  python restoration_workflow.py --input datasets/test_small.jpg --output-dir results/test --skip-detection
        """
    )

    # Input/Output
    parser.add_argument('--input', required=True, help='Input document image')
    parser.add_argument('--output-dir', required=True, help='Output directory for all results')

    # Detection parameters
    parser.add_argument('--method', default='lab_b', choices=['lab_b', 'hsv', 'lab_a'], help='Detection method (default: lab_b)')
    parser.add_argument('--threshold', type=int, default=138, help='LAB b-channel threshold (default: 138)')
    parser.add_argument('--min-area', type=int, default=50, help='Minimum hole area in pixels (default: 50)')
    parser.add_argument('--max-area', type=int, default=2500000, help='Maximum hole area in pixels (default: 2500000)')
    parser.add_argument('--svg-simplify', type=float, default=0.1, help='SVG simplification level (default: 0.1)')

    # Layout parameters
    parser.add_argument('--paper-size', default='A4', choices=['A4', 'A3'], help='Paper size for cutting layout (default: A4)')

    # Workflow control
    parser.add_argument('--skip-detection', action='store_true', help='Skip hole detection (use existing results)')
    parser.add_argument('--skip-layout', action='store_true', help='Skip cutting layout generation')
    parser.add_argument('--skip-guide', action='store_true', help='Skip restoration guide generation')

    args = parser.parse_args()

    print("=" * 60)
    print("Integrated Restoration Workflow")
    print("조선시대 문서 복원 통합 워크플로우")
    print("=" * 60)
    print(f"\nInput: {args.input}")
    print(f"Output: {args.output_dir}")
    print()

    start_time = time.time()

    # 출력 디렉토리 구조
    detection_dir = os.path.join(args.output_dir, 'detection')
    svg_dir = os.path.join(args.output_dir, 'detection', 'svg_vectors')
    layout_dir = os.path.join(args.output_dir, 'cutting_layout')
    guide_dir = os.path.join(args.output_dir, 'restoration_guide')

    # Step 1: Hole Detection
    if not args.skip_detection:
        cmd = [
            'python', 'extract_whiteness_based.py',
            '--input', args.input,
            '--method', args.method,
            '--s-threshold', str(args.threshold),
            '--min-area', str(args.min_area),
            '--max-area', str(args.max_area),
            '--crop-document',
            '--corner-method', 'edges',
            '--export-svg',
            '--svg-simplify', str(args.svg_simplify),
            '--svg-individual',
            '--output-dir', detection_dir
        ]

        if not run_command(cmd, "1. Hole Detection"):
            print("\nWorkflow stopped due to error in hole detection")
            return 1
    else:
        print("\n[Skipping hole detection - using existing results]")

    # Step 1.5: Verify SVG files exist
    if not os.path.exists(svg_dir) or len(list(Path(svg_dir).glob('*.svg'))) == 0:
        print(f"\nError: No SVG files found in {svg_dir}")
        print("Please run hole detection first or check the output directory")
        return 1

    svg_count = len(list(Path(svg_dir).glob('*.svg')))
    print(f"\nFound {svg_count} SVG pieces for layout and guide generation")

    # Step 2: Cutting Layout
    if not args.skip_layout:
        cmd = [
            'python', 'create_cutting_layout.py',
            '--svg-dir', svg_dir,
            '--output-dir', layout_dir,
            '--paper-size', args.paper_size
        ]

        if not run_command(cmd, "2. Cutting Layout Generation"):
            print("\nWarning: Layout generation failed, but continuing...")
    else:
        print("\n[Skipping cutting layout generation]")

    # Step 3: Restoration Guide
    if not args.skip_guide:
        cmd = [
            'python', 'create_restoration_guide.py',
            '--image', args.input,
            '--svg-dir', svg_dir,
            '--output-dir', guide_dir
        ]

        if not run_command(cmd, "3. Restoration Guide Generation"):
            print("\nWarning: Guide generation failed, but continuing...")
    else:
        print("\n[Skipping restoration guide generation]")

    # Summary
    elapsed_time = time.time() - start_time

    print("\n" + "=" * 60)
    print("Workflow Completed!")
    print("=" * 60)
    print(f"\nTotal time: {elapsed_time:.1f} seconds")
    print(f"\nOutput structure:")
    print(f"  {args.output_dir}/")
    print(f"    ├─ detection/")
    print(f"    │  ├─ document_boundary.png    - Document boundary detection")
    print(f"    │  ├─ comparison.png            - Hole detection visualization")
    print(f"    │  ├─ holes_combined.svg        - All holes in one SVG file")
    print(f"    │  └─ svg_vectors/              - Individual SVG pieces ({svg_count} files)")
    print(f"    ├─ cutting_layout/")
    print(f"    │  ├─ cutting_layout_page_*.svg - Laser cutting layouts")
    print(f"    │  └─ cutting_layout_info.json  - Layout metadata")
    print(f"    └─ restoration_guide/")
    print(f"       ├─ restoration_guide.png     - Detailed guide with numbers")
    print(f"       ├─ simple_overlay.png        - Simple numbered overlay")
    print(f"       └─ piece_locations.csv       - Piece coordinate data")
    print()
    print("Next steps:")
    print("  1. Print cutting_layout_page_*.svg files")
    print("  2. Use laser cutter to cut the pieces")
    print("  3. Use restoration_guide.png to see where each piece goes")
    print("  4. Refer to piece_locations.csv for exact coordinates")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
