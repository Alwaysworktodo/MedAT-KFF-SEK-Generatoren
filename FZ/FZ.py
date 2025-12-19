import argparse
import random
import math
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import black, lightgrey, grey
from shapely.geometry import Polygon as ShapelyPolygon, Point, LineString
from shapely.ops import split, unary_union
import datetime
import os
import traceback

# --- 1. Geometrische Formen und Operationen ---

class Shape:
    def __init__(self, vertices):
        self.vertices = np.array(vertices, dtype=float)
        self.shapely_polygon = ShapelyPolygon(self.vertices) if len(self.vertices) > 2 else None

    def get_bounding_box(self):
        if len(self.vertices) == 0: return 0, 0, 0, 0
        min_x, max_x = np.min(self.vertices[:, 0]), np.max(self.vertices[:, 0])
        min_y, max_y = np.min(self.vertices[:, 1]), np.max(self.vertices[:, 1])
        return min_x, min_y, max_x, max_y

    def rotate(self, angle_degrees, center=None):
        if center is None: center = np.mean(self.vertices, axis=0)
        angle_radians = math.radians(angle_degrees)
        rot_mat = np.array([[math.cos(angle_radians),-math.sin(angle_radians)],[math.sin(angle_radians),math.cos(angle_radians)]])
        self.vertices = np.dot(self.vertices - center, rot_mat.T) + center
        self.shapely_polygon = ShapelyPolygon(self.vertices) if len(self.vertices) > 2 else None
        return self

    def draw_on_canvas(self, canvas, x_offset, y_offset, scale=1.0, fill_color=black, stroke_color=black, stroke_width=0.1):
        if len(self.vertices) < 3: return
        path = canvas.beginPath()
        path.moveTo(x_offset+self.vertices[0][0]*scale, y_offset+self.vertices[0][1]*scale)
        for v in self.vertices[1:]: path.lineTo(x_offset+v[0]*scale, y_offset+v[1]*scale)
        path.close()
        canvas.setFillColor(fill_color); canvas.setStrokeColor(stroke_color); canvas.setLineWidth(stroke_width)
        canvas.drawPath(path, fill=1, stroke=1)

    def __eq__(self, other):
        if not isinstance(other, Shape): return NotImplemented
        if self.shapely_polygon and other.shapely_polygon:
            return self.shapely_polygon.equals_exact(other.shapely_polygon, tolerance=0.01)
        return False

    def __hash__(self):
        if self.shapely_polygon: return hash(tuple(sorted([round(c,2) for p in self.vertices for c in p])))
        return hash(tuple(map(tuple, self.vertices)))

class Polygon(Shape):
    def __init__(self, num_sides, size, center=(0,0)):
        angles = np.linspace(0, 2*np.pi, num_sides, endpoint=False)
        super().__init__([(center[0]+size*math.cos(a), center[1]+size*math.sin(a)) for a in angles])

class OrientedPolygon(Polygon):
    def __init__(self, num_sides, size, center=(0,0)):
        super().__init__(num_sides, size, center)
        if num_sides % 2 != 0: self.rotate(90 + 180 / num_sides)
        else: self.rotate(90)

class CircleSegment(Shape):
    def __init__(self, total_angle_degrees, radius, center=(0,0)):
        vertices = [center]
        for i in range(51):
            angle = math.radians(total_angle_degrees*i/50)
            vertices.append((center[0]+radius*math.cos(angle), center[1]+radius*math.sin(angle)))
        super().__init__(vertices)

class Rectangle(Shape):
    def __init__(self, width, height, center=(0,0)):
        w,h = width/2, height/2
        super().__init__([(center[0]-w,center[1]-h),(center[0]+w,center[1]-h),(center[0]+w,center[1]+h),(center[0]-w,center[1]+h)])

class Rhombus(Shape):
    def __init__(self, width, height, center=(0,0)):
        w,h = width/2, height/2
        super().__init__([(center[0],center[1]-h),(center[0]+w,center[1]),(center[0],center[1]+h),(center[0]-w,center[1])])

class Trapezoid(Shape):
    def __init__(self, top_width, bottom_width, height, center=(0,0)):
        bw,tw,h = bottom_width/2,top_width/2,height/2
        super().__init__([(center[0]-bw,center[1]-h),(center[0]+bw,center[1]-h),(center[0]+tw,center[1]+h),(center[0]-tw,center[1]+h)])

class Parallelogram(Shape):
    def __init__(self, width, height, shear, center=(0,0)):
        w, h = width/2, height/2
        super().__init__([(center[0]-w-shear,center[1]-h),(center[0]+w-shear,center[1]-h),(center[0]+w+shear,center[1]+h),(center[0]-w+shear,center[1]+h)])


# --- 2. Erweiterte Fragmentierung mit Schwierigkeitsgraden ---
def create_simple_splitter(bounds):
    minx, miny, maxx, maxy = bounds
    p1, p2 = Point(random.uniform(minx,maxx), random.uniform(miny,maxy)), Point(random.uniform(minx,maxx), random.uniform(miny,maxy))
    if p1.equals(p2): return None
    vec = np.array([p2.x-p1.x, p2.y-p1.y]); norm = np.linalg.norm(vec)
    if norm == 0: return None
    vec /= norm
    diag = math.sqrt((maxx-minx)**2 + (maxy-miny)**2) * 1.5
    return LineString([Point(p1.x-vec[0]*diag, p1.y-vec[1]*diag), Point(p2.x+vec[0]*diag, p2.y+vec[1]*diag)])

def create_complex_splitter(bounds):
    minx, miny, maxx, maxy = bounds
    p_start, p_end = Point(random.uniform(minx,maxx), random.uniform(miny,maxy)), Point(random.uniform(minx,maxx), random.uniform(miny,maxy))
    if p_start.equals(p_end): return None
    num_knicks = random.randint(1, 2); points = [p_start]; main_vec = np.array([p_end.x-p_start.x, p_end.y-p_start.y])
    for i in range(num_knicks):
        progress = (i+1)/(num_knicks+1); mid_point = np.array([p_start.x, p_start.y]) + main_vec*progress
        perp_vec = np.array([-main_vec[1], main_vec[0]]); offset = (random.random()-0.5) * np.linalg.norm(main_vec) * 0.4
        knick_point = mid_point + perp_vec * offset / np.linalg.norm(perp_vec); points.append(Point(knick_point))
    points.append(p_end)
    start_vec = np.array([points[1].x-points[0].x, points[1].y-points[0].y]); start_vec /= np.linalg.norm(start_vec)
    end_vec = np.array([points[-1].x-points[-2].x, points[-1].y-points[-2].y]); end_vec /= np.linalg.norm(end_vec)
    diag = math.sqrt((maxx-minx)**2 + (maxy-miny)**2) * 1.5
    points[0] = Point(points[0].x-start_vec[0]*diag, points[0].y-start_vec[1]*diag)
    points[-1] = Point(points[-1].x+end_vec[0]*diag, points[-1].y+end_vec[1]*diag)
    return LineString(points)

def create_diverse_fragments(shape, num_fragments, use_complex_cuts=False, max_piece_fraction=None):
    if not shape.shapely_polygon or shape.shapely_polygon.is_empty: return []
    MIN_FRAGMENT_AREA = 70.0
    total_area = shape.shapely_polygon.area
    max_allowed_area = None
    if max_piece_fraction is not None and max_piece_fraction > 0:
        max_allowed_area = max(0.0, float(max_piece_fraction)) * total_area
    fragments_shapely = [shape.shapely_polygon]
    attempts = 0
    # Try to reach desired count and respect max piece area if provided
    while attempts < 120:
        attempts += 1
        # Determine whether we still need to split: either not enough pieces, or a piece too large
        too_large_idxs = []
        if max_allowed_area is not None:
            too_large_idxs = [i for i,f in enumerate(fragments_shapely) if f.area > max_allowed_area * 1.001]
        need_more_pieces = len(fragments_shapely) < num_fragments

        if not need_more_pieces and not too_large_idxs:
            break

        # Build eligible list depending on goal
        eligible = []
        if too_large_idxs:
            eligible = [(i, fragments_shapely[i]) for i in too_large_idxs]
        else:
            eligible = [(i,f) for i,f in enumerate(fragments_shapely) if f.area > (MIN_FRAGMENT_AREA*2.1)]
        if not eligible:
            # Nothing eligible to split further
            break
        # Prefer splitting the largest eligible fragment (more deterministic control of max size)
        idx, frag = max(eligible, key=lambda t: t[1].area)
        splitter = create_complex_splitter(frag.bounds) if use_complex_cuts else create_simple_splitter(frag.bounds)
        if splitter is None: continue
        try:
            res = split(frag, splitter)
            new = [f for f in res.geoms if isinstance(f, ShapelyPolygon) and f.area > MIN_FRAGMENT_AREA]
            if len(new) > 1:
                fragments_shapely.pop(idx); fragments_shapely.extend(new)
        except Exception: pass
    return [Shape(list(f.exterior.coords)) for f in fragments_shapely]

# --- 3. Aufgabengenerierung mit Schwierigkeitsgraden ---
def generate_task(seed, difficulty="mixed", max_piece_fraction=0.4):
    random.seed(seed)
    use_complex_cuts = "-complex" in difficulty
    base_difficulty = difficulty.replace("-complex", "")
    if base_difficulty == "easy": num_fragments = random.randint(3, 4)
    elif base_difficulty == "medium": num_fragments = random.randint(4, 6)
    elif base_difficulty == "hard": num_fragments = random.randint(5, 7)
    else: num_fragments = random.randint(3, 7)
    
    poly_size, circle_size = 35, 40
    constructors = {
        "square": lambda: Rectangle(poly_size*1.8, poly_size*1.8), "rectangle": lambda: Rectangle(poly_size*2.2, poly_size*1.5),
        "pentagon": lambda: OrientedPolygon(5, poly_size*1.2), "hexagon": lambda: Polygon(6, poly_size*1.1),
        "heptagon": lambda: OrientedPolygon(7, poly_size*1.1), "octagon": lambda: OrientedPolygon(8, poly_size*1.1),
        "rhombus": lambda: Rhombus(poly_size*2.2, poly_size*2.2), "trapezoid": lambda: Trapezoid(poly_size*1.5, poly_size*2.5, poly_size*1.5),
        "parallelogram": lambda: Parallelogram(poly_size*2.2, poly_size*1.5, poly_size*0.4),
        "quarter_circle": lambda: CircleSegment(90, circle_size), "half_circle": lambda: CircleSegment(180, circle_size), "three_quarter_circle": lambda: CircleSegment(270, circle_size)
    }
    shape_pool = {"circle": ["quarter_circle", "half_circle", "three_quarter_circle"], "polygon": list(set(constructors.keys())-set(["quarter_circle", "half_circle", "three_quarter_circle"]))}
    target_type = random.choice(list(constructors.keys()))
    target_shape = constructors[target_type]()
    solution_fragments = create_diverse_fragments(
        target_shape,
        num_fragments,
        use_complex_cuts=use_complex_cuts,
        max_piece_fraction=max_piece_fraction,
    )
    fragment_pool = [Shape(frag.vertices.copy()).rotate(random.uniform(0, 360)) for frag in solution_fragments]
    
    is_answer_e = random.random() < 0.2
    candidate_shapes = []
    target_category = "circle" if "circle" in target_type else "polygon"

    if target_category == "circle":
        # Always use: full circle, quarter, half, three quarter
        circle_types = ["full_circle", "quarter_circle", "half_circle", "three_quarter_circle"]
        # Add constructor for full_circle if not present
        if "full_circle" not in constructors:
            constructors["full_circle"] = lambda: CircleSegment(360, circle_size)
        # Build answer options
        candidate_shapes = [constructors[t]() for t in circle_types]
        # Determine correct label
        correct_label = "E"
        if not is_answer_e:
            # Find which option matches the target shape
            for i, shape in enumerate(candidate_shapes):
                if shape == target_shape:
                    correct_label = chr(ord("A")+i)
                    break
        # If E is correct, target_shape is not among the options
        if is_answer_e:
            correct_label = "E"
    else:
        # Polygon logic as before
        if not is_answer_e:
            candidate_shapes.append(Shape(target_shape.vertices.copy()))
        distractor_pool = list(set(shape_pool[target_category]) - {target_type})
        while len(candidate_shapes) < 4:
            if not distractor_pool:
                distractor_pool = list(set(shape_pool[target_category]))
            distractor_type = random.choice(distractor_pool)
            distractor_pool.remove(distractor_type)
            candidate_shapes.append(constructors[distractor_type]())
        random.shuffle(candidate_shapes)
        correct_label = "E"
        if not is_answer_e:
            for i, shape in enumerate(candidate_shapes):
                if shape == target_shape:
                    correct_label = chr(ord("A")+i)
                    break
    return {"fragment_pool": fragment_pool, "candidate_shapes": candidate_shapes, "correct_option_label": correct_label, "solution_fragments": solution_fragments}


# --- 4. PDF-Generierung ---
def draw_visual_solution(canvas, x, y, scale, fragments):
    """Draw the assembled solution using the original fragments:
    1) Fill all fragments in grey without stroke (no overlaps visible),
    2) Draw thin internal seams (fragment outlines) in black,
    3) Draw the unioned outer contour thicker in black to avoid outer protrusions.
    """
    polys = [f.shapely_polygon for f in fragments if f.shapely_polygon and not f.shapely_polygon.is_empty]
    if not polys:
        return
    # Compute union for clean exterior outline
    try:
        union_geom = unary_union(polys).buffer(0)
    except Exception:
        union_geom = polys[0]

    def _build_path(rl_canvas, poly):
        path = rl_canvas.beginPath()
        ext = list(poly.exterior.coords)
        path.moveTo(x + ext[0][0]*scale, y + ext[0][1]*scale)
        for px, py in ext[1:]:
            path.lineTo(x + px*scale, y + py*scale)
        path.close()
        # Holes
        if poly.interiors:
            for interior in poly.interiors:
                coords = list(interior.coords)
                path.moveTo(x + coords[0][0]*scale, y + coords[0][1]*scale)
                for px, py in coords[1:]:
                    path.lineTo(x + px*scale, y + py*scale)
                path.close()
        return path

    # 1) Fill all fragments (no stroke)
    for poly in polys:
        try:
            canvas.saveState()
            canvas.setFillColor(grey)
            canvas.setStrokeColor(black)
            canvas.setLineWidth(0.1)
            path = _build_path(canvas, poly)
            canvas.drawPath(path, fill=1, stroke=0)
        finally:
            canvas.restoreState()

    # 2) Draw internal seams (thin strokes for each fragment)
    for poly in polys:
        try:
            canvas.saveState()
            canvas.setFillColor(grey)
            canvas.setStrokeColor(black)
            canvas.setLineWidth(0.25)
            path = _build_path(canvas, poly)
            canvas.drawPath(path, fill=0, stroke=1)
        finally:
            canvas.restoreState()

    # 3) Draw the union outline (thicker) on top to hide any tiny outer protrusions
    def _draw_union_outline(geom):
        if hasattr(geom, "geoms"):
            for g in geom.geoms:
                _draw_union_outline(g)
        elif isinstance(geom, ShapelyPolygon):
            canvas.saveState()
            canvas.setFillColor(grey)
            canvas.setStrokeColor(black)
            canvas.setLineWidth(1.2)
            path = _build_path(canvas, geom)
            canvas.drawPath(path, fill=0, stroke=1)
            canvas.restoreState()

    _draw_union_outline(union_geom)

def generate_pdf_perfect(tasks, output_dir, seed, n_items, difficulty):
    file_name = f"FZ_MedAT_Set_{difficulty.upper()}_{datetime.datetime.now().strftime('%Y%m%d')}_{seed}_{n_items}items.pdf"
    file_path = os.path.join(output_dir, file_name)
    try:
        c = canvas.Canvas(file_path, pagesize=A4); width, height = A4
        c.setFont("Helvetica-Bold", 24); c.drawCentredString(width/2, height-55*mm, "MedAT Übungsset FZ")
        c.setFont("Helvetica-Bold", 14); c.drawCentredString(width/2, height-70*mm, f"Schwierigkeit: {difficulty.replace('-',' ').title()}")
        c.setFont("Helvetica", 12)
        c.drawCentredString(width/2, height-85*mm, f"Datum: {datetime.datetime.now().strftime('%d.%m.%Y')}")
        c.drawCentredString(width/2, height-95*mm, f"Anzahl Aufgaben: {n_items}")
        c.drawCentredString(width/2, height-105*mm, f"Seed: {seed}")
        c.showPage()

        for i, task in enumerate(tasks):
            if i > 0 and i % 2 == 0: c.showPage()
            y_offset = height/2 if i%2 == 0 else 0
            
            frag_y_centerline = y_offset + height/2 - 45*mm
            cand_y_centerline = y_offset + 75*mm

            c.setFont("Helvetica-Bold", 14); c.drawString(20*mm, y_offset+height/2-20*mm, f"{i+1}.)")
            
            total_drawable_width = width - 60*mm
            anchor_points = [(30*mm + i * (total_drawable_width / 6)) for i in range(7)]
            
            for j, fragment in enumerate(task["fragment_pool"]):
                if j >= len(anchor_points): break
                anchor_x = anchor_points[j]
                
                centroid = fragment.shapely_polygon.centroid
                offset_x = anchor_x - centroid.x
                offset_y = frag_y_centerline - centroid.y

                fragment.draw_on_canvas(c, offset_x, offset_y, scale=1.0)
            
            cand_space = (width-2*30*mm-35*mm)/4.5
            for j, candidate in enumerate(task["candidate_shapes"]):
                x_pos = 35*mm + j*cand_space
                candidate.draw_on_canvas(c, x_pos, cand_y_centerline, scale=0.75)
                c.setFont("Helvetica", 12); c.drawCentredString(x_pos+12*mm, cand_y_centerline-25*mm, f"({chr(ord('A')+j)})")
            
            e_x, e_y = 35*mm+4*cand_space+12*mm, cand_y_centerline
            c.setFont("Helvetica", 10); c.drawCentredString(e_x, e_y, "Keine der"); c.drawCentredString(e_x, e_y-4*mm, "Antwortmöglichkeiten"); c.drawCentredString(e_x, e_y-8*mm, "ist richtig.")
            c.setFont("Helvetica", 12); c.drawCentredString(e_x, e_y-25*mm, "(E)")
        c.showPage()
        
        c.setFont("Helvetica-Bold", 16); c.drawCentredString(width/2, height-40*mm, "Antwortbogen")
        c.setFont("Helvetica", 12); start_y_ans = height-60*mm
        for i in range(n_items):
            y = start_y_ans - (i*10*mm)
            c.drawString(40*mm, y, f"Aufgabe {i + 1}:")
            for j, opt in enumerate(["A","B","C","D","E"]):
                c.rect(80*mm+j*20*mm, y-1, 4*mm, 4*mm, fill=0, stroke=1); c.drawString(80*mm+j*20*mm+6*mm, y, opt)
        c.showPage()

        c.setFont("Helvetica-Bold", 16); c.setFillColor(black); c.drawCentredString(width/2, height-30*mm, "Lösungen")
        items_per_page = 5; row_height = 55*mm; start_y_sol = height-50*mm
        for i, task in enumerate(tasks):
            if i > 0 and i%items_per_page == 0:
                c.showPage(); c.setFont("Helvetica-Bold", 16); c.setFillColor(black); c.drawCentredString(width/2, height-30*mm, "Lösungen (Fortsetzung)")
            idx_on_page = i % items_per_page; y_pos = start_y_sol - idx_on_page*row_height
            c.setFont("Helvetica-Bold", 12); c.setFillColor(black); c.drawString(30*mm, y_pos, f"Aufgabe {i+1}:   {task['correct_option_label']}")
            if task["solution_fragments"]:
                draw_visual_solution(c, 100*mm, y_pos-15*mm, 0.75, task["solution_fragments"])
            c.line(20*mm, y_pos-row_height+15*mm, width-20*mm, y_pos-row_height+15*mm)
        c.showPage()
        
        c.save()
        print(f"--- ERFOLG! PDF wurde erfolgreich generiert: {file_path} ---")
    except Exception:
        print("\n!!! FEHLER BEIM ERSTELLEN DES PDF !!!"); traceback.print_exc()

# --- 5. Hauptfunktion und CLI ---
def main():
    difficulty_choices = ['easy', 'easy-complex', 'medium', 'medium-complex', 'hard', 'hard-complex', 'mixed', 'mixed-complex']
    parser = argparse.ArgumentParser(description="Generiert MedAT FZ Übungshefte.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--n-items", type=int, default=15, help="Anzahl der Aufgaben pro Set.")
    parser.add_argument("--out-dir", type=str, default=".", help="Ausgabeverzeichnis.")
    parser.add_argument("--seed", type=int, default=random.randint(1, 10000), help="Zufalls-Seed.")
    parser.add_argument("--difficulty", type=str, default="mixed", choices=difficulty_choices, help="Schwierigkeitsgrad des Sets.")
    parser.add_argument("--max-piece-fraction", type=float, default=0.4, help="Maximaler Flächenanteil eines einzelnen Teilstücks an der Zielfigur (z.B. 0.4 = 40%).")
    parser.add_argument("--batch-count", type=int, default=1, help="Wie viele PDFs sollen erstellt werden?")
    args = parser.parse_args()

    # Validierung der max-piece-fraction
    if args.max_piece_fraction is not None:
        if not (0.05 <= args.max_piece_fraction <= 0.95):
            print(f"Hinweis: --max-piece-fraction {args.max_piece_fraction} liegt außerhalb des empfohlenen Bereichs [0.05, 0.95]. Wert wird begrenzt.")
            args.max_piece_fraction = max(0.05, min(0.95, args.max_piece_fraction))

    if not os.path.exists(args.out_dir):
        try:
            os.makedirs(args.out_dir)
            print(f"Verzeichnis '{args.out_dir}' erstellt.")
        except OSError as e:
            print(f"!!! FEHLER: Konnte Verzeichnis nicht erstellen: {e} !!!")
            return

    # Batch-Erstellung
    for batch_idx in range(args.batch_count):
        batch_seed = args.seed + batch_idx * args.n_items
        print(f"\n--- Erstelle PDF {batch_idx+1}/{args.batch_count} mit Seed {batch_seed} ---")
        tasks = [generate_task(batch_seed + i, args.difficulty, max_piece_fraction=args.max_piece_fraction) for i in range(args.n_items)]
        generate_pdf_perfect(tasks, args.out_dir, batch_seed, args.n_items, args.difficulty)

if __name__ == "__main__":
    main()