#!/usr/bin/env python3
"""
Laser Cutting Layout Generator
조선시대 문서 복원을 위한 레이저 커팅 레이아웃 자동 생성

기능:
- 개별 SVG 파일들을 A4/A3 용지에 자동 배치 (bin packing)
- 각 조각에 번호 부여
- 레이저 커터용 다중 페이지 SVG/PDF 생성
"""

import os
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
import json
from typing import List, Dict, Tuple
import math

# A4 크기 (mm) - 여백 고려
A4_WIDTH = 210 - 20  # 양쪽 10mm 여백
A4_HEIGHT = 297 - 20  # 위아래 10mm 여백

# A3 크기 (mm) - 여백 고려
A3_WIDTH = 297 - 20
A3_HEIGHT = 420 - 20

# 조각 간 간격 (mm) - 비싼 종이 절약
PIECE_SPACING = 1.5


class SVGPiece:
    """SVG 조각 정보"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.filename = os.path.basename(file_path)

        # SVG 파일 파싱
        tree = ET.parse(file_path)
        root = tree.getroot()

        # 네임스페이스 처리
        ns = {'svg': 'http://www.w3.org/2000/svg'}

        # 크기 정보 추출
        width_str = root.get('width', '0mm')
        height_str = root.get('height', '0mm')

        # mm 단위로 변환
        self.width = float(width_str.replace('mm', ''))
        self.height = float(height_str.replace('mm', ''))

        # 메타데이터 추출
        self.metadata = {}
        metadata_elem = root.find('svg:metadata', ns) or root.find('metadata') or root.find('{http://www.w3.org/2000/svg}metadata')

        if metadata_elem is not None:
            for child in metadata_elem:
                tag = child.tag.replace('{http://www.w3.org/2000/svg}', '')
                self.metadata[tag] = child.text

        # hole_id 추출
        self.hole_id = int(self.metadata.get('hole_id', 0))

        # 원본 위치 정보
        self.original_position = self.metadata.get('original_position', '')
        self.bbox = self.metadata.get('bbox', '')

        # 배치 위치 (나중에 계산됨)
        self.placed_x = 0
        self.placed_y = 0
        self.page_number = 0

        # 스케일 팩터 (기본값 1.0 = 원본 크기)
        self.scale = 1.0

        # 원본 크기 저장 (스케일 적용 전)
        self.original_width = self.width
        self.original_height = self.height

        # SVG 경로 데이터 저장 - 네임스페이스 고려
        self.path_element = (root.find('.//svg:path', ns) or
                            root.find('.//path') or
                            root.find('.//{http://www.w3.org/2000/svg}path'))
        self.viewBox = root.get('viewBox', '')

    def apply_scale(self, scale_factor: float):
        """스케일 팩터 적용 (크기 조정)"""
        self.scale = scale_factor
        self.width = self.original_width * scale_factor
        self.height = self.original_height * scale_factor

    def get_scaled_size(self) -> Tuple[float, float]:
        """스케일이 적용된 크기 반환"""
        return (self.width, self.height)

    def __repr__(self):
        return f"SVGPiece(id={self.hole_id}, {self.width:.1f}x{self.height:.1f}mm)"


class BinPacker2D:
    """2D Bin Packing Algorithm (Shelf-based)"""

    def __init__(self, width: float, height: float):
        self.width = width
        self.height = height
        self.shelves = []
        self.placed_pieces = []

    def can_fit(self, piece: SVGPiece) -> bool:
        """조각이 현재 페이지에 들어갈 수 있는지 확인"""
        piece_w = piece.width + PIECE_SPACING
        piece_h = piece.height + PIECE_SPACING

        # 기존 선반에 배치 시도
        for shelf in self.shelves:
            if shelf['current_x'] + piece_w <= self.width and piece_h <= shelf['height']:
                return True

        # 새 선반 생성 가능 여부 확인
        if len(self.shelves) == 0:
            next_y = 0
        else:
            next_y = self.shelves[-1]['y'] + self.shelves[-1]['height']

        if next_y + piece_h <= self.height and piece_w <= self.width:
            return True

        return False

    def add_piece(self, piece: SVGPiece) -> bool:
        """조각을 현재 페이지에 배치"""
        piece_w = piece.width + PIECE_SPACING
        piece_h = piece.height + PIECE_SPACING

        # 기존 선반에 배치 시도
        for shelf in self.shelves:
            if shelf['current_x'] + piece_w <= self.width and piece_h <= shelf['height']:
                # 배치 가능
                piece.placed_x = shelf['current_x']
                piece.placed_y = shelf['y']
                shelf['current_x'] += piece_w
                self.placed_pieces.append(piece)
                return True

        # 새 선반 생성
        if len(self.shelves) == 0:
            next_y = 0
        else:
            next_y = self.shelves[-1]['y'] + self.shelves[-1]['height']

        if next_y + piece_h <= self.height and piece_w <= self.width:
            # 새 선반 추가
            new_shelf = {
                'y': next_y,
                'height': piece_h,
                'current_x': piece_w
            }
            self.shelves.append(new_shelf)

            piece.placed_x = 0
            piece.placed_y = next_y
            self.placed_pieces.append(piece)
            return True

        return False


def load_svg_pieces(svg_dir: str) -> List[SVGPiece]:
    """SVG 디렉토리에서 모든 조각 로드"""
    pieces = []

    svg_files = sorted(Path(svg_dir).glob('*.svg'))

    print(f"Loading {len(svg_files)} SVG pieces from {svg_dir}...")

    for svg_file in svg_files:
        try:
            piece = SVGPiece(str(svg_file))
            pieces.append(piece)
            if piece.path_element is None:
                print(f"Warning: No path element found in {svg_file.name}")
        except Exception as e:
            print(f"Warning: Failed to load {svg_file}: {e}")

    print(f"Successfully loaded {len(pieces)} pieces")

    # hole_id 순으로 정렬 (번호 순서)
    pieces.sort(key=lambda p: p.hole_id)

    return pieces


def pack_pieces_to_pages(pieces: List[SVGPiece], paper_size: str = 'A4') -> List[BinPacker2D]:
    """조각들을 여러 페이지에 배치"""

    # 용지 크기 설정
    if paper_size.upper() == 'A4':
        page_width = A4_WIDTH
        page_height = A4_HEIGHT
    elif paper_size.upper() == 'A3':
        page_width = A3_WIDTH
        page_height = A3_HEIGHT
    else:
        raise ValueError(f"Unsupported paper size: {paper_size}")

    print(f"\nPacking {len(pieces)} pieces onto {paper_size} pages ({page_width}x{page_height}mm)...")

    pages = []
    current_page = BinPacker2D(page_width, page_height)
    pages.append(current_page)

    for i, piece in enumerate(pieces):
        # 현재 페이지에 배치 시도
        if not current_page.add_piece(piece):
            # 현재 페이지에 못 들어가면 새 페이지 생성
            current_page = BinPacker2D(page_width, page_height)
            pages.append(current_page)

            if not current_page.add_piece(piece):
                print(f"Warning: Piece {piece.hole_id} is too large for a single page!")
                continue

        # 페이지 번호 기록
        piece.page_number = len(pages)

        if (i + 1) % 50 == 0:
            print(f"  Packed {i + 1}/{len(pieces)} pieces...")

    print(f"Total pages required: {len(pages)}")

    return pages


def create_cutting_layout_svg(pages: List[BinPacker2D], output_dir: str, paper_size: str = 'A4'):
    """레이저 커팅용 SVG 레이아웃 생성"""

    if paper_size.upper() == 'A4':
        page_width = A4_WIDTH + 20  # 여백 포함 전체 크기
        page_height = A4_HEIGHT + 20
        margin = 10
    elif paper_size.upper() == 'A3':
        page_width = A3_WIDTH + 20
        page_height = A3_HEIGHT + 20
        margin = 10
    else:
        raise ValueError(f"Unsupported paper size: {paper_size}")

    os.makedirs(output_dir, exist_ok=True)

    print(f"\nGenerating {len(pages)} page(s) of cutting layouts...")

    layout_info = []

    for page_num, page in enumerate(pages, 1):
        # SVG 파일 생성
        svg = ET.Element('svg', {
            'xmlns': 'http://www.w3.org/2000/svg',
            'width': f'{page_width}mm',
            'height': f'{page_height}mm',
            'viewBox': f'0 0 {page_width} {page_height}'
        })

        # 메타데이터
        metadata = ET.SubElement(svg, 'metadata')
        ET.SubElement(metadata, 'page_number').text = str(page_num)
        ET.SubElement(metadata, 'total_pages').text = str(len(pages))
        ET.SubElement(metadata, 'paper_size').text = paper_size
        ET.SubElement(metadata, 'piece_count').text = str(len(page.placed_pieces))

        # 용지 경계 표시 (레이저 커터에서는 무시됨, 시각화용)
        page_border = ET.SubElement(svg, 'rect', {
            'x': '0',
            'y': '0',
            'width': f'{page_width}',
            'height': f'{page_height}',
            'fill': 'none',
            'stroke': '#cccccc',
            'stroke-width': '0.5',
            'stroke-dasharray': '2,2'
        })

        # 페이지 정보 텍스트
        page_info = ET.SubElement(svg, 'text', {
            'x': f'{margin}',
            'y': '5',
            'font-family': 'Arial',
            'font-size': '3',
            'fill': '#999999'
        })
        page_info.text = f'Page {page_num}/{len(pages)} - {paper_size} - {len(page.placed_pieces)} pieces'

        # 각 조각 배치
        page_layout_info = {
            'page': page_num,
            'pieces': []
        }

        for piece in page.placed_pieces:
            # 조각 그룹 생성
            piece_group = ET.SubElement(svg, 'g', {
                'id': f'piece_{piece.hole_id}',
                'data-hole-id': str(piece.hole_id),
                'data-original-pos': piece.original_position
            })

            # 조각 위치 (여백 고려)
            x_offset = margin + piece.placed_x
            y_offset = margin + piece.placed_y

            # 원본 SVG의 path를 복사하되, 위치 조정
            if piece.path_element is not None:
                path_d = piece.path_element.get('d', '')

                # ViewBox에서 원본 좌표 범위 추출
                vb_x, vb_y, vb_w, vb_h = 0, 0, piece.width, piece.height

                if piece.viewBox:
                    vb_parts = piece.viewBox.split()
                    if len(vb_parts) == 4:
                        vb_x = float(vb_parts[0])
                        vb_y = float(vb_parts[1])
                        vb_w = float(vb_parts[2])
                        vb_h = float(vb_parts[3])

                # 스케일 계산 (viewBox 크기 -> 물리적 크기)
                # piece.scale 팩터 적용하여 확대/축소
                scale_x = (piece.width / vb_w * piece.scale) if vb_w > 0 else piece.scale
                scale_y = (piece.height / vb_h * piece.scale) if vb_h > 0 else piece.scale

                # Transform 설정: 원본 좌표를 페이지 좌표로 변환 + 스케일 적용
                transform = f'translate({x_offset}, {y_offset}) scale({scale_x}, {scale_y}) translate({-vb_x}, {-vb_y})'

                piece_path = ET.SubElement(piece_group, 'path', {
                    'd': path_d,
                    'fill': 'none',
                    'stroke': 'black',
                    'stroke-width': '0.1',
                    'vector-effect': 'non-scaling-stroke',
                    'transform': transform
                })

            # 번호 표시 (조각 중앙) - 작은 조각도 보이도록 크기 줄임
            text_x = x_offset + piece.width / 2
            text_y = y_offset + piece.height / 2

            # 번호 크기를 조각 크기에 맞춰 조정 (최소 0.8mm, 최대 2.0mm)
            number_font_size = min(2.0, max(0.8, min(piece.width, piece.height) / 3))
            bg_radius = number_font_size * 0.8

            # 배경 원 (가독성)
            bg_circle = ET.SubElement(piece_group, 'circle', {
                'cx': f'{text_x}',
                'cy': f'{text_y}',
                'r': f'{bg_radius}',
                'fill': 'white',
                'fill-opacity': '0.9',
                'class': 'number-bg'  # 레이저 커터용에서 제거 가능
            })

            # 번호 텍스트
            number_text = ET.SubElement(piece_group, 'text', {
                'x': f'{text_x}',
                'y': f'{text_y + number_font_size * 0.3}',
                'text-anchor': 'middle',
                'font-family': 'Arial',
                'font-size': f'{number_font_size}',
                'font-weight': 'bold',
                'fill': 'red',
                'class': 'number-text'  # 레이저 커터용에서 제거 가능
            })
            number_text.text = str(piece.hole_id)

            # 레이아웃 정보 저장
            page_layout_info['pieces'].append({
                'hole_id': piece.hole_id,
                'position_on_page': f'{x_offset:.2f}, {y_offset:.2f}',
                'size': f'{piece.width:.2f}x{piece.height:.2f}mm',
                'original_position': piece.original_position,
                'bbox': piece.bbox
            })

        layout_info.append(page_layout_info)

        # 1. 가이드용 SVG 저장 (번호 포함)
        svg_guide_filename = f'cutting_layout_page_{page_num:02d}_with_numbers.svg'
        svg_guide_path = os.path.join(output_dir, svg_guide_filename)

        tree = ET.ElementTree(svg)
        ET.indent(tree, space='  ')
        tree.write(svg_guide_path, encoding='utf-8', xml_declaration=True)

        print(f"  Created: {svg_guide_filename} ({len(page.placed_pieces)} pieces, with numbers)")

        # 2. 레이저 커터용 SVG 생성 (번호 제거)
        svg_laser = ET.Element('svg', {
            'xmlns': 'http://www.w3.org/2000/svg',
            'width': f'{page_width}mm',
            'height': f'{page_height}mm',
            'viewBox': f'0 0 {page_width} {page_height}'
        })

        # 메타데이터 복사
        metadata_laser = ET.SubElement(svg_laser, 'metadata')
        ET.SubElement(metadata_laser, 'page_number').text = str(page_num)
        ET.SubElement(metadata_laser, 'total_pages').text = str(len(pages))
        ET.SubElement(metadata_laser, 'paper_size').text = paper_size
        ET.SubElement(metadata_laser, 'piece_count').text = str(len(page.placed_pieces))

        # path 요소만 복사 (번호 없이)
        for piece_group in svg.findall('.//g[@id]'):
            piece_group_laser = ET.SubElement(svg_laser, 'g', piece_group.attrib)

            # path만 복사
            for path in piece_group.findall('.//path'):
                ET.SubElement(piece_group_laser, 'path', path.attrib)

        # 레이저용 SVG 저장
        svg_laser_filename = f'cutting_layout_page_{page_num:02d}_for_laser.svg'
        svg_laser_path = os.path.join(output_dir, svg_laser_filename)

        tree_laser = ET.ElementTree(svg_laser)
        ET.indent(tree_laser, space='  ')
        tree_laser.write(svg_laser_path, encoding='utf-8', xml_declaration=True)

        print(f"  Created: {svg_laser_filename} (for laser cutter, no numbers)")

    # 레이아웃 정보 JSON 저장
    json_path = os.path.join(output_dir, 'cutting_layout_info.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(layout_info, f, indent=2, ensure_ascii=False)

    print(f"\nLayout info saved to: cutting_layout_info.json")

    return layout_info


def main():
    parser = argparse.ArgumentParser(description='Generate laser cutting layout from individual SVG pieces')
    parser.add_argument('--svg-dir', required=True, help='Directory containing individual SVG files')
    parser.add_argument('--output-dir', default='cutting_layout', help='Output directory for layout files')
    parser.add_argument('--paper-size', default='A4', choices=['A4', 'A3'], help='Paper size (default: A4)')

    # 스케일 옵션
    parser.add_argument('--scale', type=float, default=1.0, help='Global scale factor for all pieces (default: 1.0)')
    parser.add_argument('--scale-config', type=str, help='JSON file with individual piece scales (format: {"hole_id": scale, ...})')

    args = parser.parse_args()

    print("=" * 60)
    print("Laser Cutting Layout Generator")
    print("문화재 복원용 레이저 커팅 레이아웃 자동 생성")
    print("=" * 60)

    # 1. SVG 조각 로드
    pieces = load_svg_pieces(args.svg_dir)

    if len(pieces) == 0:
        print("Error: No SVG pieces found!")
        return

    # 2. 스케일 적용
    individual_scales = {}
    if args.scale_config:
        try:
            with open(args.scale_config, 'r', encoding='utf-8') as f:
                individual_scales = json.load(f)
            print(f"\nLoaded individual scale config from {args.scale_config}")
            print(f"  Individual scales defined for {len(individual_scales)} pieces")
        except Exception as e:
            print(f"\nWarning: Failed to load scale config: {e}")
            print("  Using global scale only")

    # 스케일 적용
    if args.scale != 1.0 or individual_scales:
        print(f"\nApplying scale factors:")
        print(f"  Global scale: {args.scale}x")

        individual_count = 0
        for piece in pieces:
            # 개별 스케일이 정의되어 있으면 우선 사용
            piece_id_str = str(piece.hole_id)
            if piece_id_str in individual_scales:
                scale_factor = float(individual_scales[piece_id_str])
                piece.apply_scale(scale_factor)
                individual_count += 1
            else:
                # 전체 스케일 적용
                piece.apply_scale(args.scale)

        if individual_count > 0:
            print(f"  Applied individual scales to {individual_count} pieces")
        if args.scale != 1.0:
            global_count = len(pieces) - individual_count
            print(f"  Applied global scale ({args.scale}x) to {global_count} pieces")

    # 통계 출력
    total_area = sum(p.width * p.height for p in pieces)
    print(f"\nStatistics:")
    print(f"  Total pieces: {len(pieces)}")
    print(f"  Total area: {total_area:.2f} mm²")
    print(f"  Largest piece: {max(pieces, key=lambda p: p.width * p.height)}")
    print(f"  Smallest piece: {min(pieces, key=lambda p: p.width * p.height)}")

    # 2. 페이지에 배치
    pages = pack_pieces_to_pages(pieces, args.paper_size)

    # 3. SVG 레이아웃 생성
    layout_info = create_cutting_layout_svg(pages, args.output_dir, args.paper_size)

    print("\n" + "=" * 60)
    print("Layout generation completed!")
    print(f"  Output directory: {args.output_dir}")
    print(f"  Total pages: {len(pages)}")
    print(f"  Total pieces: {len(pieces)}")
    print("=" * 60)


if __name__ == '__main__':
    main()
