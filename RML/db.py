import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rml_database.db")


def get_db():
    """Return a SQLite3 connection with row_factory set to sqlite3.Row."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


CATALOG_PRODUCTS = [
    # Paints & Thinners
    ("Paints & Thinners", "KB Denatured Alcohol", "Standard alcohol solvent for cleaning and thinning", "bottle", 45.00, 80, 15, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Paints & Thinners", "KB Paint Thinner", "Standard mineral spirit paint thinner", "bottle", 65.00, 120, 20, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Paints & Thinners", "Tower Lacquer Thinner", "High grade automotive and wood lacquer thinner", "bottle", 45.00, 90, 20, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Paints & Thinners", "Centro Varnish Maple", "Wood finish varnish in maple shade", "bottle", 70.00, 60, 10, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Paints & Thinners", "Centro Varnish Brown", "Wood finish varnish in brown shade", "bottle", 70.00, 60, 10, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Paints & Thinners", "Centro Varnish Natural", "Wood finish varnish in natural clear shade", "bottle", 70.00, 60, 10, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Paints & Thinners", "Centro Varnish Mahogany", "Wood finish varnish in mahogany red-brown shade", "bottle", 70.00, 60, 10, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Paints & Thinners", "Solignum Wood Preservative (1L)", "All-weather anti-termite wood preservative 1 Liter", "can", 860.00, 35, 10, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Paints & Thinners", "Solignum Wood Preservative (4L)", "All-weather anti-termite wood preservative 1 Gallon", "can", 1850.00, 20, 5, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),

    # Adhesives & Sealants
    ("Adhesives & Sealants", "Rugby Contact Cement (Small)", "High strength general purpose contact adhesive small can", "can", 45.00, 150, 25, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Adhesives & Sealants", "Rugby Contact Cement (Big)", "High strength general purpose contact adhesive big can", "can", 110.00, 100, 20, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Adhesives & Sealants", "Vulcaseal Elastomeric Sealant (75ml)", "Elastomeric roof and gutter sealant 75ml pouch", "pouch", 90.00, 200, 30, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Adhesives & Sealants", "Vulcaseal Elastomeric Sealant (1/4L)", "Elastomeric roof and gutter sealant 1/4 Liter can", "can", 295.00, 80, 15, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Adhesives & Sealants", "Vulcaseal Elastomeric Sealant (1/2L)", "Elastomeric roof and gutter sealant 1/2 Liter can", "can", 498.00, 50, 10, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Adhesives & Sealants", "Vulcaseal Elastomeric Sealant (1L)", "Elastomeric roof and gutter sealant 1 Liter can", "can", 800.00, 40, 10, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Adhesives & Sealants", "ElastoSeal (Small)", "High-grade waterproofing elastomeric sealant small pouch", "pouch", 85.00, 120, 20, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Adhesives & Sealants", "ElastoSeal (Medium)", "High-grade waterproofing elastomeric sealant medium pouch", "pouch", 170.00, 90, 15, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Adhesives & Sealants", "No More Nails Adhesive (Small)", "Heavy duty instant grab construction adhesive small tube", "tube", 65.00, 80, 15, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Adhesives & Sealants", "No More Nails Adhesive (Medium)", "Heavy duty instant grab construction adhesive medium tube", "tube", 110.00, 75, 15, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Adhesives & Sealants", "No More Nails Adhesive (Large)", "Heavy duty instant grab construction adhesive large tube", "tube", 255.00, 50, 10, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Adhesives & Sealants", "Solvent Cement Pipe Glue", "Standard solvent cement for PVC pipes", "can", 95.00, 100, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Adhesives & Sealants", "Neltex PVC Pipe Cement (Small)", "Premium solvent cement for pressure and drain pipes small", "can", 145.00, 85, 15, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Adhesives & Sealants", "Neltex PVC Pipe Cement (Medium)", "Premium solvent cement for pressure and drain pipes medium", "can", 175.00, 70, 15, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Adhesives & Sealants", "Neltex PVC Pipe Cement (Large)", "Premium solvent cement for pressure and drain pipes large", "can", 275.00, 55, 10, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Adhesives & Sealants", "Stikwel Wood Glue (250g)", "Fast bonding water-resistant PVA wood glue 250g", "bottle", 65.00, 90, 15, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Adhesives & Sealants", "Stikwel Wood Glue (500g)", "Fast bonding water-resistant PVA wood glue 500g", "bottle", 170.00, 75, 15, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Adhesives & Sealants", "Stikwel Wood Glue (1kg)", "Fast bonding water-resistant PVA wood glue 1kg jar", "jar", 350.00, 60, 10, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Adhesives & Sealants", "Stikwel Wood Glue (4kg)", "Fast bonding water-resistant PVA wood glue 4kg gallon", "gallon", 900.00, 30, 5, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),

    # Tapes, Wires & Fasteners
    ("Tapes, Wires & Fasteners", "E-Tape Electrical Tape (Small)", "PVC flame-retardant electrical insulating tape small", "roll", 25.00, 250, 40, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Tapes, Wires & Fasteners", "E-Tape Electrical Tape (Medium)", "PVC flame-retardant electrical insulating tape medium", "roll", 70.00, 150, 30, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Tapes, Wires & Fasteners", "Masking Tape 1/2\"", "General purpose painter masking tape 1/2 inch", "roll", 40.00, 180, 25, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Tapes, Wires & Fasteners", "Masking Tape 3/4\"", "General purpose painter masking tape 3/4 inch", "roll", 55.00, 160, 25, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Tapes, Wires & Fasteners", "Masking Tape 1\"", "General purpose painter masking tape 1 inch", "roll", 65.00, 140, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Tapes, Wires & Fasteners", "Teflon Tape (Small)", "PTFE plumbing thread seal tape small spool", "roll", 15.00, 300, 50, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Tapes, Wires & Fasteners", "Teflon Tape (Medium)", "PTFE plumbing thread seal tape medium spool", "roll", 20.00, 250, 40, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Tapes, Wires & Fasteners", "G.I. Tie Wire #16", "Galvanized iron tie wire gauge 16 per kilo", "kg", 100.00, 500, 50, "https://images.unsplash.com/photo-1535813547-99c456a41d4a?w=500"),
    ("Tapes, Wires & Fasteners", "G.I. Tie Wire #18", "Galvanized iron tie wire gauge 18 per kilo", "kg", 110.00, 450, 50, "https://images.unsplash.com/photo-1535813547-99c456a41d4a?w=500"),
    ("Tapes, Wires & Fasteners", "Bistayan Wire Mesh Screen", "Galvanized screen wire mesh 1 meter length", "meter", 100.00, 180, 20, "https://images.unsplash.com/photo-1535813547-99c456a41d4a?w=500"),

    # Cement & Aggregates
    ("Cement & Aggregates", "Fortune Cement (40kg)", "High performance Portland Pozzolan cement 40kg bag", "bag", 220.00, 400, 60, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Cement & Aggregates", "Holcim Cement (40kg)", "Premium structural blended cement 40kg bag", "bag", 220.00, 450, 60, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Cement & Aggregates", "Panambak Regular Filling Material", "Soil and earth backfill material per load", "load", 1900.00, 25, 5, "https://images.unsplash.com/photo-1508873535684-277a3cbcc4e8?w=500"),
    ("Cement & Aggregates", "Panambak Dump Truck Load", "Heavy dump truckload site filling material", "truckload", 8000.00, 15, 3, "https://images.unsplash.com/photo-1508873535684-277a3cbcc4e8?w=500"),
    ("Cement & Aggregates", "Boulder Mini Dump Load", "Foundation and riprap boulders mini dump load", "load", 4800.00, 18, 4, "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=500"),
    ("Cement & Aggregates", "White Sand Truckload", "Plastering and masonry white sand full truckload", "truckload", 6000.00, 20, 5, "https://images.unsplash.com/photo-1508873535684-277a3cbcc4e8?w=500"),
    ("Cement & Aggregates", "S1 Screened Sand Truckload", "Fine concrete screened S1 sand full truckload", "truckload", 5000.00, 22, 5, "https://images.unsplash.com/photo-1508873535684-277a3cbcc4e8?w=500"),
    ("Cement & Aggregates", "Crushed Gravel 3/4\" (Truckload)", "Coarse aggregate 3/4 inch crushed gravel truckload", "truckload", 5000.00, 25, 5, "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=500"),
    ("Cement & Aggregates", "Crushed Gravel 3/8\" (Truckload)", "Fine pea gravel 3/8 inch crushed aggregate truckload", "truckload", 4800.00, 20, 5, "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=500"),

    # Steel & Rebar
    ("Steel & Rebar", "Steel Rebar 9mm x 6m", "Grade 33/40 deformed steel rebar 9mm diameter 6m", "pc", 130.00, 220, 30, "https://images.unsplash.com/photo-1535813547-99c456a41d4a?w=500"),
    ("Steel & Rebar", "Steel Rebar 10mm x 6m", "Grade 33/40 deformed steel rebar 10mm diameter 6m", "pc", 170.00, 280, 35, "https://images.unsplash.com/photo-1535813547-99c456a41d4a?w=500"),
    ("Steel & Rebar", "Steel Rebar 16mm x 6m", "Grade 40 deformed steel rebar 16mm diameter 6m", "pc", 440.00, 180, 25, "https://images.unsplash.com/photo-1535813547-99c456a41d4a?w=500"),
    ("Steel & Rebar", "Yero Corrugated G.I. Sheet 8ft", "Galvanized corrugated metal roof sheet 8 feet", "sheet", 464.00, 120, 20, "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=500"),
    ("Steel & Rebar", "Yero Corrugated G.I. Sheet 10ft", "Galvanized corrugated metal roof sheet 10 feet", "sheet", 580.00, 100, 15, "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=500"),
    ("Steel & Rebar", "Yero Corrugated G.I. Sheet 12ft", "Galvanized corrugated metal roof sheet 12 feet", "sheet", 696.00, 90, 15, "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=500"),
    ("Steel & Rebar", "Plain G.I. Sheet 3' x 8'", "Smooth galvanized sheet metal 3ft x 8ft gauge", "sheet", 580.00, 75, 15, "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=500"),
    ("Steel & Rebar", "Plain G.I. Sheet 4' x 8'", "Smooth galvanized sheet metal 4ft x 8ft gauge", "sheet", 680.00, 65, 10, "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=500"),
    ("Steel & Rebar", "Welding Rod (Ordinary)", "E6013 mild steel welding electrode per kilo", "kg", 130.00, 160, 20, "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=500"),
    ("Steel & Rebar", "Welding Rod (Special)", "High tensile specialized welding electrode per kilo", "kg", 200.00, 80, 15, "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=500"),
    ("Steel & Rebar", "Welding Rod (Stainless)", "Stainless steel welding electrode per piece", "pc", 20.00, 300, 40, "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=500"),

    # Boards & Lumber
    ("Boards & Lumber", "Ordinary Plywood 1/4\"", "Standard interior grade ordinary plywood 4'x8' 1/4 inch", "sheet", 550.00, 140, 20, "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=500"),
    ("Boards & Lumber", "Ordinary Plywood 1/2\"", "Standard interior grade ordinary plywood 4'x8' 1/2 inch", "sheet", 950.00, 95, 15, "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=500"),
    ("Boards & Lumber", "Ordinary Plywood 3/4\"", "Standard interior grade ordinary plywood 4'x8' 3/4 inch", "sheet", 1800.00, 60, 10, "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=500"),
    ("Boards & Lumber", "Marine Plywood 1/4\"", "Waterproof phenolic resin bonded marine plywood 4'x8' 1/4\"", "sheet", 600.00, 130, 20, "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=500"),
    ("Boards & Lumber", "Marine Plywood 1/2\"", "Waterproof phenolic resin bonded marine plywood 4'x8' 1/2\"", "sheet", 1100.00, 90, 15, "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=500"),
    ("Boards & Lumber", "Marine Plywood 3/4\"", "Waterproof phenolic resin bonded marine plywood 4'x8' 3/4\"", "sheet", 2000.00, 55, 10, "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=500"),
    ("Boards & Lumber", "Shena Board 1/4\"", "Composite decorative ceiling and wall board 1/4 inch", "sheet", 500.00, 70, 15, "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=500"),

    # Lighting & Fixtures
    ("Lighting & Fixtures", "Opple LED Bulb 5W", "Energy saving Opple daylight LED bulb 5 Watts", "pc", 70.00, 180, 25, "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=500"),
    ("Lighting & Fixtures", "Opple LED Bulb 15W", "Energy saving Opple daylight LED bulb 15 Watts", "pc", 170.00, 120, 20, "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=500"),
    ("Lighting & Fixtures", "Opple LED Bulb 18W", "High lumen Opple daylight LED bulb 18 Watts", "pc", 190.00, 110, 20, "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=500"),
    ("Lighting & Fixtures", "Alco LED Bulb 7W", "Alco bright daylight energy LED bulb 7 Watts", "pc", 85.00, 160, 25, "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=500"),
    ("Lighting & Fixtures", "Alco LED Bulb 9W", "Alco bright daylight energy LED bulb 9 Watts", "pc", 95.00, 150, 20, "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=500"),
    ("Lighting & Fixtures", "Alco LED Bulb 12W", "Alco bright daylight energy LED bulb 12 Watts", "pc", 110.00, 140, 20, "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=500"),
    ("Lighting & Fixtures", "Alco LED Bulb 15W", "Alco bright daylight energy LED bulb 15 Watts", "pc", 120.00, 130, 20, "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=500"),
    ("Lighting & Fixtures", "Alco LED Bulb 18W", "Alco bright daylight energy LED bulb 18 Watts", "pc", 190.00, 100, 15, "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=500"),
    ("Lighting & Fixtures", "Focus LED Bulb 5W", "Focus brand high lumen LED bulb 5 Watts", "pc", 75.00, 120, 20, "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=500"),
    ("Lighting & Fixtures", "Focus LED Bulb 7W", "Focus brand high lumen LED bulb 7 Watts", "pc", 90.00, 110, 20, "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=500"),
    ("Lighting & Fixtures", "Focus LED Bulb 12W", "Focus brand high lumen LED bulb 12 Watts", "pc", 130.00, 95, 15, "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=500"),
    ("Lighting & Fixtures", "Philips LED Bulb 3W", "Philips genuine eye comfort LED bulb 3 Watts", "pc", 95.00, 140, 20, "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=500"),
    ("Lighting & Fixtures", "Philips LED Bulb 5W", "Philips genuine eye comfort LED bulb 5 Watts", "pc", 105.00, 150, 20, "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=500"),
    ("Lighting & Fixtures", "Philips LED Bulb 7W", "Philips genuine eye comfort LED bulb 7 Watts", "pc", 115.00, 160, 20, "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=500"),
    ("Lighting & Fixtures", "Philips LED Bulb 9W", "Philips genuine eye comfort LED bulb 9 Watts", "pc", 125.00, 170, 25, "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=500"),
    ("Lighting & Fixtures", "Philips LED Bulb 12W", "Philips genuine eye comfort LED bulb 12 Watts", "pc", 189.00, 120, 20, "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=500"),
    ("Lighting & Fixtures", "Fluorescent Tube 18W/20W", "T8 daylight straight fluorescent tube 18W/20W", "pc", 150.00, 90, 15, "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=500"),
    ("Lighting & Fixtures", "Fluorescent Tube 36W", "T8 daylight straight fluorescent tube 36W (4ft)", "pc", 210.00, 80, 15, "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=500"),
    ("Lighting & Fixtures", "Fluorescent Ballast 20W", "Standard ballast for 20W fluorescent lamps", "pc", 250.00, 60, 10, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Lighting & Fixtures", "Fluorescent Ballast 40W", "Standard ballast for 40W fluorescent lamps", "pc", 310.00, 50, 10, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Lighting & Fixtures", "Fluorescent Fixture Set 20W", "Complete 20W lamp fixture housing with starter & ballast", "set", 360.00, 45, 10, "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=500"),
    ("Lighting & Fixtures", "Fluorescent Fixture Set 36W", "Complete 36W 4ft lamp fixture housing set", "set", 420.00, 40, 10, "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=500"),
    ("Lighting & Fixtures", "Octagonal Junction Box (Without Cover)", "PVC octagonal ceiling junction box without cover", "pc", 35.00, 300, 40, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Lighting & Fixtures", "Octagonal Junction Box (With Cover)", "PVC octagonal ceiling junction box with snap cover", "pc", 65.00, 250, 30, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Lighting & Fixtures", "Utility Box 2x4 (PVC)", "Standard electrical flush surface utility box 2x4", "pc", 35.00, 400, 50, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),

    # Plumbing & Fittings
    ("Plumbing & Fittings", "Neltex PVC Pipe Black 1/2\"", "Neltex polyethylene high-density water pipe 1/2 inch", "pc", 130.00, 150, 25, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Neltex PVC Pipe Black 3/4\"", "Neltex polyethylene high-density water pipe 3/4 inch", "pc", 165.00, 130, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Neltex PVC Sanitary Pipe 1/2\"", "Neltex orange sanitary drainage pipe 1/2 inch", "pc", 145.00, 120, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Neltex PVC Sanitary Pipe 1\"", "Neltex orange sanitary drainage pipe 1 inch", "pc", 230.00, 110, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Neltex PVC Sanitary Pipe 2\"", "Neltex orange sanitary drainage pipe 2 inch", "pc", 370.00, 140, 25, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Neltex PVC Sanitary Pipe 3\"", "Neltex orange sanitary drainage pipe 3 inch", "pc", 880.00, 90, 15, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Neltex PVC Sanitary Pipe 4\"", "Neltex orange sanitary drainage pipe 4 inch", "pc", 980.00, 85, 15, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Bio Pipe 2\"", "Eco sanitary drainage conduit pipe 2 inch", "pc", 210.00, 100, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Bio Pipe 3\"", "Eco sanitary drainage conduit pipe 3 inch", "pc", 380.00, 80, 15, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Bio Pipe 4\"", "Eco sanitary drainage conduit pipe 4 inch", "pc", 420.00, 75, 15, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "PVC Elbow Black 2\"", "Black poly drain elbow 90 degrees 2 inch", "pc", 20.00, 200, 30, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "PVC Elbow Black 3\"", "Black poly drain elbow 90 degrees 3 inch", "pc", 40.00, 170, 25, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "PVC Elbow Black 4\"", "Black poly drain elbow 90 degrees 4 inch", "pc", 55.00, 150, 25, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "PVC Tee Black 2 x 2", "Black poly pipe tee joint 2x2", "pc", 20.00, 180, 25, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "PVC Tee Black 2 x 3", "Black poly pipe tee joint 2x3 reducer", "pc", 35.00, 140, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "PVC Tee Black 2 x 4", "Black poly pipe tee joint 2x4 reducer", "pc", 45.00, 130, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Clean Out Plug 2\"", "PVC threaded inspection clean out plug 2 inch", "pc", 20.00, 160, 25, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Clean Out Plug 3\"", "PVC threaded inspection clean out plug 3 inch", "pc", 30.00, 140, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Clean Out Plug 4\"", "PVC threaded inspection clean out plug 4 inch", "pc", 40.00, 130, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Neltex Sanitary Elbow 2\" 90°", "Neltex sanitary curve elbow 2 inch 90 degrees", "pc", 95.00, 140, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Neltex Sanitary Elbow 2\" 45°", "Neltex sanitary curve elbow 2 inch 45 degrees", "pc", 65.00, 150, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Neltex Sanitary Elbow 3\" 90°", "Neltex sanitary curve elbow 3 inch 90 degrees", "pc", 120.00, 120, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Neltex Sanitary Elbow 3\" 45°", "Neltex sanitary curve elbow 3 inch 45 degrees", "pc", 90.00, 130, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Neltex Sanitary Elbow 4\" 90°", "Neltex sanitary curve elbow 4 inch 90 degrees", "pc", 145.00, 110, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Neltex Sanitary Elbow 4\" 45°", "Neltex sanitary curve elbow 4 inch 45 degrees", "pc", 110.00, 120, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Sanitary P-Trap with Plug", "Standard self-sealing water seal P-trap fitting", "pc", 90.00, 100, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Neltex Cleanout Cover 2 x 2", "Neltex threaded clean out adapter & cover 2x2", "pc", 75.00, 110, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Neltex Cleanout Cover 3 x 3", "Neltex threaded clean out adapter & cover 3x3", "pc", 90.00, 100, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Neltex Cleanout Cover 3 x 2", "Neltex reducer clean out adapter & cover 3x2", "pc", 130.00, 80, 15, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Neltex WYE Fitting 2 x 2", "Neltex sanitary branch 45 deg WYE fitting 2x2", "pc", 55.00, 130, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Neltex WYE Fitting 3 x 3", "Neltex sanitary branch 45 deg WYE fitting 3x3", "pc", 85.00, 110, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Neltex WYE Fitting 4 x 3", "Neltex sanitary branch 45 deg WYE fitting 4x3", "pc", 120.00, 90, 15, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Neltex WYE Fitting 4 x 4", "Neltex sanitary branch 45 deg WYE fitting 4x4", "pc", 145.00, 85, 15, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Sanitary TEE Fitting 2 x 2", "Sanitary flow curved tee fitting 2x2", "pc", 55.00, 130, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Sanitary TEE Fitting 3 x 2", "Sanitary flow curved tee fitting 3x2", "pc", 75.00, 110, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Sanitary TEE Fitting 3 x 3", "Sanitary flow curved tee fitting 3x3", "pc", 85.00, 100, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Sanitary TEE Fitting 4 x 2", "Sanitary flow curved tee fitting 4x2", "pc", 95.00, 90, 15, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Sanitary TEE Fitting 4 x 3", "Sanitary flow curved tee fitting 4x3", "pc", 110.00, 85, 15, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Sanitary TEE Fitting 4 x 4", "Sanitary flow curved tee fitting 4x4", "pc", 125.00, 80, 15, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),
    ("Plumbing & Fittings", "Plastic Faucet (Standard)", "Durable PVC threaded outdoor and garden bibcock faucet", "pc", 50.00, 220, 30, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500"),

    # Tools, Hardware & Safety
    ("Tools, Hardware & Safety", "Bisagra Hinges 3\" x 3\"", "Heavy duty steel loose pin door/cabinet hinges 3\"x3\"", "pair", 75.00, 160, 25, "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=500"),
    ("Tools, Hardware & Safety", "Bisagra Hinges 3 1/2\" x 3 1/2\"", "Heavy duty steel loose pin door hinges 3.5\"x3.5\"", "pair", 85.00, 140, 25, "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=500"),
    ("Tools, Hardware & Safety", "Safety Helmet (Hard Hat)", "Industrial high-density site safety helmet with chin strap", "pc", 280.00, 95, 20, "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=500"),
    ("Tools, Hardware & Safety", "Steel Wire Brush (Heavy Duty)", "Hardened steel wire scratch brush for rust and paint removal", "pc", 60.00, 130, 20, "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=500"),
    ("Tools, Hardware & Safety", "Cut-off Blade (Metal Disc)", "Reinforced 14\" metal cut-off chop saw disc", "pc", 200.00, 110, 20, "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=500"),
    ("Tools, Hardware & Safety", "Paint Roller Brush with Handle", "7-inch paint roller complete with ergonomic cage handle", "pc", 110.00, 140, 25, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Tools, Hardware & Safety", "Paint Roller Brush Refill", "7-inch synthetic nap paint roller replacement refill", "pc", 45.00, 200, 30, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500"),
    ("Tools, Hardware & Safety", "Heavy Duty Rubber Gloves", "Chemical and abrasion resistant textured rubber work gloves", "pair", 50.00, 250, 40, "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=500"),
]


def seed_catalog(cur):
    """Seed comprehensive catalog categories and products into database."""
    new_categories = [
        ("Cement & Aggregates", "Cement, sand, gravel, and concrete mixes"),
        ("Masonry", "Hollow blocks, culverts, and bricks"),
        ("Steel & Rebar", "Deformed steel bars and roofing sheets"),
        ("Boards & Lumber", "Plywood, gypsum boards, and framing"),
        ("Pipes & Electrical", "PVC pipes, fittings, and electrical supplies"),
        ("Paints & Thinners", "Paints, thinners, varnishes, and wood preservatives"),
        ("Adhesives & Sealants", "Contact cement, silicones, gap fillers, and pipe cements"),
        ("Tapes, Wires & Fasteners", "Electrical tapes, masking tapes, tie wire, and teflon"),
        ("Lighting & Fixtures", "LED bulbs, fluorescent tubes, fixtures, and enclosures"),
        ("Plumbing & Fittings", "Pipes, elbows, tees, wyes, cleanouts, and sanitary fittings"),
        ("Tools, Hardware & Safety", "Hinges, brushes, blades, hard hats, and PPE"),
    ]
    for cat_name, cat_desc in new_categories:
        cur.execute("INSERT OR IGNORE INTO categories (name, description) VALUES (?, ?)", (cat_name, cat_desc))

    cat_map = {row[1]: row[0] for row in cur.execute("SELECT id, name FROM categories").fetchall()}

    for cat_name, name, desc, unit, price, stock, threshold, img in CATALOG_PRODUCTS:
        cid = cat_map.get(cat_name)
        if not cid:
            continue
        exists = cur.execute("SELECT id FROM products WHERE name = ?", (name,)).fetchone()
        if not exists:
            cur.execute(
                """
                INSERT INTO products (category_id, name, description, unit, price, stock_quantity, low_stock_threshold, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (cid, name, desc, unit, price, stock, threshold, img)
            )


def init_db():
    """Create tables if they do not exist, run migrations, and seed sample data."""
    conn = get_db()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id TEXT UNIQUE,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            address TEXT,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'customer', 'driver', 'staff')),
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            unit TEXT NOT NULL,
            price REAL NOT NULL,
            stock_quantity INTEGER NOT NULL DEFAULT 0,
            low_stock_threshold INTEGER NOT NULL DEFAULT 20,
            image_url TEXT,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS inventory_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            movement_type TEXT NOT NULL CHECK(movement_type IN ('stock_in', 'stock_out', 'adjustment')),
            quantity INTEGER NOT NULL,
            remarks TEXT,
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS trucks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            truck_code TEXT NOT NULL UNIQUE,
            plate_number TEXT NOT NULL UNIQUE,
            capacity TEXT,
            status TEXT NOT NULL DEFAULT 'available' CHECK(status IN ('available', 'in_transit', 'maintenance'))
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_code TEXT NOT NULL UNIQUE,
            customer_id INTEGER NOT NULL,
            recipient_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            delivery_address TEXT NOT NULL,
            preferred_date TEXT,
            delivery_slot TEXT,
            special_instructions TEXT,
            subtotal REAL NOT NULL DEFAULT 0,
            delivery_fee REAL NOT NULL DEFAULT 1500,
            vat_amount REAL NOT NULL DEFAULT 0,
            total_amount REAL NOT NULL DEFAULT 0,
            order_status TEXT NOT NULL DEFAULT 'pending'
                CHECK(order_status IN ('pending', 'approved', 'rejected', 'preparing', 'in_transit', 'delivered')),
            rejection_reason TEXT,
            approval_notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (customer_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL UNIQUE,
            method TEXT NOT NULL CHECK(method IN ('cash', 'qr')),
            reference_number TEXT,
            receipt_note TEXT,
            payer_name TEXT,
            bank_used TEXT,
            proof_file TEXT,
            amount REAL NOT NULL,
            payment_status TEXT NOT NULL DEFAULT 'pending'
                CHECK(payment_status IN ('pending', 'verified', 'rejected')),
            paid_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            delivery_code TEXT NOT NULL UNIQUE,
            order_id INTEGER NOT NULL UNIQUE,
            driver_id INTEGER,
            truck_id INTEGER,
            delivery_window TEXT,
            delivery_status TEXT NOT NULL DEFAULT 'queued'
                CHECK(delivery_status IN ('queued', 'assigned', 'loading', 'en_route', 'delivered')),
            current_lat REAL DEFAULT 13.9411,
            current_lng REAL DEFAULT 121.1631,
            last_gps_update TEXT,
            recipient_received_by TEXT,
            recipient_role TEXT,
            delivery_notes TEXT,
            quantity_received TEXT,
            completion_time TEXT,
            recipient_acknowledged INTEGER DEFAULT 0,
            proof_file TEXT,
            delivered_at TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (driver_id) REFERENCES users(id),
            FOREIGN KEY (truck_id) REFERENCES trucks(id)
        );
        """
    )

    # Migrations for existing tables if columns are missing
    table_migrations = [
        ("orders", "approval_notes", "TEXT"),
        ("payments", "payer_name", "TEXT"),
        ("payments", "bank_used", "TEXT"),
        ("payments", "proof_file", "TEXT"),
        ("deliveries", "quantity_received", "TEXT"),
        ("deliveries", "completion_time", "TEXT"),
        ("deliveries", "recipient_acknowledged", "INTEGER DEFAULT 0"),
        ("deliveries", "proof_file", "TEXT"),
    ]
    for tbl, col, col_def in table_migrations:
        try:
            cols = [r[1] for r in cur.execute(f"PRAGMA table_info({tbl})").fetchall()]
            if col not in cols:
                cur.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_def}")
        except Exception:
            pass

    user_count = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        users_seed = [
            ("RML-ADM-001", "RML Admin", "admin@rml.com", "09175550100", "Purok 6, Brgy. Antipolo del Sur, Lipa City, Batangas", generate_password_hash("admin123"), "admin"),
            ("RML-DRV-014", "Juan Dela Cruz", "driver@rml.com", "09175550140", "Brgy. Marawoy, Lipa City, Batangas", generate_password_hash("driver123"), "driver"),
            ("RML-he DRV-015", "Ricardo Santos", "ricardo@rml.com", "09175551234", "Brgy. Tambo, Lipa City, Batangas", generate_password_hash("driver123"), "driver"),
            (None, "John Doe", "customer@rml.com", "09123456789", "123 Construction Ave, Lipa City, Batangas", generate_password_hash("customer123"), "customer"),
            (None, "Santos Residence", "santos@example.com", "09175550128", "Lot 12, Purok 3, Brgy. Tambo, Lipa City, Batangas", generate_password_hash("customer123"), "customer"),
            (None, "Mendoza Builders", "mendoza@example.com", "09185550199", "Brgy. Marawoy, Lipa City, Batangas", generate_password_hash("customer123"), "customer"),
        ]
        cur.executemany(
            "INSERT INTO users (staff_id, name, email, phone, address, password_hash, role) VALUES (?, ?, ?, ?, ?, ?, ?)",
            users_seed,
        )

        categories_seed = [
            ("Cement & Aggregates", "Cement, sand, gravel, and concrete mixes"),
            ("Masonry", "Hollow blocks, culverts, and bricks"),
            ("Steel & Rebar", "Deformed steel bars and roofing sheets"),
            ("Boards & Lumber", "Plywood, gypsum boards, and framing"),
            ("Pipes & Electrical", "PVC pipes, fittings, and electrical supplies"),
        ]
        cur.executemany("INSERT INTO categories (name, description) VALUES (?, ?)", categories_seed)

        products_seed = [
            (1, "Portland Cement (40kg)", "Structural Grade Type 1P", "bag", 285.00, 320, 50, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500&auto=format&fit=crop"),
            (1, "Washed River Sand", "Fine grade per cubic yard", "cu.yd", 1240.00, 45, 10, "https://images.unsplash.com/photo-1508873535684-277a3cbcc4e8?w=500&auto=format&fit=crop"),
            (1, "Crushed Gravel (3/4\")", "Concrete aggregate per ton", "ton", 980.00, 60, 15, "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=500&auto=format&fit=crop"),
            (2, "Hollow Blocks (4\")", "Load-bearing unit price", "pc", 18.50, 2400, 300, "https://images.unsplash.com/photo-1590069261209-f8e9b8642343?w=500&auto=format&fit=crop"),
            (3, "Steel Rebar (12mm)", "Deformed bar per 6m length", "pc", 312.00, 18, 25, "https://images.unsplash.com/photo-1535813547-99c456a41d4a?w=500&auto=format&fit=crop"),
            (4, "Gypsum Board (12mm)", "Standard 4'x8' sheet", "sheet", 580.00, 85, 20, "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=500&auto=format&fit=crop"),
            (5, "PVC Pipe 4\" (Orange)", "Sanitary pipe 3m length", "pc", 420.00, 110, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500&auto=format&fit=crop"),
            (3, "Corrugated Roof Sheet", "Pre-painted GI sheet 8ft", "sheet", 640.00, 14, 20, "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=500&auto=format&fit=crop"),
        ]
        cur.executemany(
            "INSERT INTO products (category_id, name, description, unit, price, stock_quantity, low_stock_threshold, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            products_seed,
        )

        trucks_seed = [
            ("RML-07", "NCB 4821", "6-Wheeler Dump Truck (10 tons)", "in_transit"),
            ("RML-03", "RML-778", "Flatbed Cargo Truck (8 tons)", "available"),
            ("RML-05", "NAA 3019", "Mini Elf Delivery Truck (4 tons)", "available"),
        ]
        cur.executemany(
            "INSERT INTO trucks (truck_code, plate_number, capacity, status) VALUES (?, ?, ?, ?)",
            trucks_seed,
        )

        cur.executemany(
            "INSERT INTO inventory_logs (product_id, movement_type, quantity, remarks, created_by) VALUES (?, ?, ?, ?, ?)",
            [
                (1, "stock_in", 400, "Weekly cement supplier restock", 1),
                (1, "stock_out", 80, "Order #RML-1051 dispatch", 1),
                (5, "stock_out", 30, "Order #RML-1052 allocation", 1),
            ],
        )

        cur.execute(
            """
            INSERT INTO orders (order_code, customer_id, recipient_name, phone, delivery_address, preferred_date, delivery_slot, subtotal, delivery_fee, vat_amount, total_amount, order_status)
            VALUES ('#RML-9042', 4, 'John Doe', '09123456789', '123 Construction Ave, Lipa City, Batangas', '2026-11-14', 'Morning (08:00 - 12:00)', 16210.00, 1500.00, 1945.20, 19655.20, 'in_transit')
            """
        )
        o1 = cur.lastrowid
        cur.executemany(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, ?, ?, ?)",
            [(o1, 1, 50, 285.00, 14250.00), (o1, 3, 2, 980.00, 1960.00)],
        )
        cur.execute(
            "INSERT INTO payments (order_id, method, reference_number, amount, payment_status) VALUES (?, 'cash', 'COD-9042', 19655.20, 'pending')",
            (o1,),
        )
        cur.execute(
            """
            INSERT INTO deliveries (delivery_code, order_id, driver_id, truck_id, delivery_window, delivery_status, current_lat, current_lng)
            VALUES ('DLV-1109-02', ?, 2, 1, '09:00 - 10:00', 'en_route', 13.9455, 121.1610)
            """,
            (o1,),
        )

        cur.execute(
            """
            INSERT INTO orders (order_code, customer_id, recipient_name, phone, delivery_address, preferred_date, delivery_slot, subtotal, delivery_fee, vat_amount, total_amount, order_status)
            VALUES ('#1051', 5, 'Engr. Paolo Santos', '09175550128', 'Lot 12, Purok 3, Brgy. Tambo, Lipa City, Batangas', '2026-11-15', 'Morning (08:00 - 12:00)', 22800.00, 1500.00, 2736.00, 27036.00, 'approved')
            """
        )
        o2 = cur.lastrowid
        cur.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES (?, 1, 80, 285.00, 22800.00)",
            (o2,),
        )
        cur.execute(
            "INSERT INTO payments (order_id, method, reference_number, amount, payment_status) VALUES (?, 'qr', 'GCASH-88342190', 27036.00, 'pending')",
            (o2,),
        )

        cur.execute(
            """
            INSERT INTO orders (order_code, customer_id, recipient_name, phone, delivery_address, preferred_date, delivery_slot, subtotal, delivery_fee, vat_amount, total_amount, order_status)
            VALUES ('#1052', 6, 'Mendoza Builders', '09185550199', 'Brgy. Marawoy, Lipa City, Batangas', '2026-11-14', 'Afternoon (13:00 - 17:00)', 9360.00, 1500.00, 1123.20, 11983.20, 'approved')
            """
        )
        o3 = cur.lastrowid
        cur.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES (?, 5, 30, 312.00, 9360.00)",
            (o3,),
        )
        cur.execute(
            "INSERT INTO payments (order_id, method, reference_number, amount, payment_status) VALUES (?, 'qr', 'MAYA-901234', 11983.20, 'verified')",
            (o3,),
        )
        cur.execute(
            """
            INSERT INTO deliveries (delivery_code, order_id, driver_id, truck_id, delivery_window, delivery_status, current_lat, current_lng)
            VALUES ('DLV-1109-03', ?, 2, 1, '13:00 - 14:00', 'loading', 13.9411, 121.1631)
            """,
            (o3,),
        )

    # Seed or expand full hardware catalog
    seed_catalog(cur)

    conn.commit()
    conn.close()
