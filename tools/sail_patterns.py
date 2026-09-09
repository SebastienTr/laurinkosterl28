"""Generate original, model-fitted sail patterns and a thread schedule from saved interfaces."""
import json
import math
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build'
OUT = BUILD / 'sails'
OUT.mkdir(exist_ok=True)
rig = json.loads((BUILD / 'rigging.json').read_text())
points = rig['points_mm']
def distance(a, b): return math.dist(a, b)
def toward(a, b, length):
    d = distance(a, b)
    return [a[i] + (b[i] - a[i]) * length / d for i in range(3)]
# Finished mainsail luff and foot follow the 1998 handbook at 1:30.
# Leech is the straight chord that fits this model; no historical roach is claimed.
tack = [113.8, 0, 79.5]
head = toward(tack, [tack[0]+4, 0, tack[2]+361], 9400/30)
clew = [223.8, 0, 80.23]
fore = points['FORESTAY']
jib_tack = [fore[0]+1, 0, fore[2]+3]
jib_head = toward(jib_tack, points['MASTHEAD_FORWARD'], 10400/30)
sails = [dict(name='Mainsail', tack=tack, head=head, clew=clew),
         dict(name='Genoa', tack=jib_tack, head=jib_head, clew=[148,0,63])]
for sail in sails:
    a,b,c = sail['tack'],sail['head'],sail['clew']
    luff,foot,leech = distance(a,b),distance(a,c),distance(b,c)
    y = (foot*foot+luff*luff-leech*leech)/(2*luff)
    x = math.sqrt(max(0,foot*foot-y*y))
    sail.update(luff_mm=luff,foot_mm=foot,leech_mm=leech,pattern_mm=[[0,0],[0,luff],[x,y]])
    assert sail['head'][2] < points['MASTHEAD_FORWARD'][2]
    assert x < 170 and luff < 400
(OUT/'sail_dimensions.json').write_text(json.dumps({'scale':30,'purpose':'Flat display sails fitted to this model; not full-size sailmaking plans','hem_allowance_mm':0,'sails':sails},indent=2)+'\n')
# Four A4 pages: two overlapping tiles per sail, 15 mm shared strip.
pdf=canvas.Canvas(str(OUT/'Laurine_Sails_1-30.pdf'),pagesize=(210*mm,297*mm),invariant=1)
pdf.setTitle('Laurine - 1:30 sail cutting patterns')
pdf.setAuthor('Laurine model project')
for sail in sails:
    for tile in range(2):
        pdf.setFont('Helvetica-Bold',15);pdf.drawString(15*mm,279*mm,f"{sail['name']} | {'lower' if tile==0 else 'upper'} tile")
        pdf.setFont('Helvetica',9)
        pdf.drawString(15*mm,272*mm,'Print at 100% / Actual size. Disable Fit to page.')
        pdf.drawString(15*mm,266*mm,'Solid outline = cut edge. No hem allowance. Join matching cross marks.')
        pdf.drawString(15*mm,260*mm,f"Luff {sail['luff_mm']:.1f} / foot {sail['foot_mm']:.1f} / leech {sail['leech_mm']:.1f} mm")
        # Physical pattern origin is x=24 mm, y=34 mm; each tile covers 205 mm.
        offset=tile*190
        pdf.saveState();clip=pdf.beginPath();clip.rect(20*mm,30*mm,175*mm,211*mm);pdf.clipPath(clip,stroke=0)
        pdf.translate(24*mm,(34-offset)*mm)
        path=pdf.beginPath()
        a,b,c=sail['pattern_mm'];path.moveTo(a[0]*mm,a[1]*mm)
        for x,y in [b,c,a]:path.lineTo(x*mm,y*mm)
        pdf.setLineWidth(.45);pdf.drawPath(path)
        # Registration marks in the 190..205 mm overlap, identical on both tiles.
        pdf.setDash(2,2);pdf.line(-3*mm,197*mm,160*mm,197*mm);pdf.setDash()
        for x in (10,150):
            pdf.line((x-2)*mm,197*mm,(x+2)*mm,197*mm)
            pdf.line(x*mm,195*mm,x*mm,199*mm)
        pdf.setFont('Helvetica',7);pdf.drawString(20*mm,199*mm,'Match this line and both crosses')
        pdf.restoreState()
        pdf.setLineWidth(.6);pdf.line(24*mm,19*mm,74*mm,19*mm)
        for x in (24,74):pdf.line(x*mm,17*mm,x*mm,21*mm)
        pdf.setFont('Helvetica',8);pdf.drawString(80*mm,18*mm,'50 mm calibration - measure before cutting')
        pdf.setFont('Helvetica',7);pdf.drawString(15*mm,9*mm,'Model-fitted flat sails. Test in paper first. Reinforce corners before adding thread.')
        pdf.showPage()
pdf.save()
lines=['# Sail dimensions and thread lengths','', 'All measurements are millimetres on the 1:30 model. Thread lengths include 40 mm for knot tails.', '', '| Sail | Luff | Foot | Leech |','|---|---:|---:|---:|']
for s in sails:lines.append(f"| {s['name']} | {s['luff_mm']:.1f} | {s['foot_mm']:.1f} | {s['leech_mm']:.1f} |")
lines+=['','| Thread | Attachment sequence | Cut length |','|---|---|---:|']
for r in rig['routes']:lines.append(f"| {r['name']} | {' → '.join(r['points'])} | {r['cut_length_mm']} |")
lines+=['','Add two 450 mm halyards (head corner → masthead eye → foot eye), two 180 mm genoa sheets (clew → side car → winch), and a 150 mm outhaul (main clew → boom end). Cut mast lacing as needed.','', 'Use the assembly guide for the installation order. These lengths are starting cuts; dry-fit and trim the tails.','']
(OUT/'CUTTING_LIST.md').write_text('\n'.join(lines))
print('Generated four A4 sail tiles and model-derived thread schedule.')
