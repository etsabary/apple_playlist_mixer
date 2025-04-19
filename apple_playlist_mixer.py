#!/usr/bin/env python3
# ---------------------------------------------------------------------------
#  Apple Playlist Mixer
#     • Hebrew‑filter option removed
#     • Mixed‑playlist files saved in their own folder
#     • ALSO exports full Apple‑playlist TSV (mixed_playlist_apple.txt)
#     • Dark‑themed Tk & PySide6 GUIs (CLI unchanged)
# ---------------------------------------------------------------------------

import os, csv, random, sys
import pandas as pd, chardet

# ─────────────────────────────────────────────────────────────────────────────
#  Folder constants
# ─────────────────────────────────────────────────────────────────────────────
INPUT_FOLDER        = 'playlists'         # where the source *.txt playlists live
CSV_FOLDER          = 'csv_playlists'     # slim 2‑column intermediates
MIXED_OUTPUT_FOLDER = 'mixed_playlists'   # final outputs
for d in (CSV_FOLDER, MIXED_OUTPUT_FOLDER):
    os.makedirs(d, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
#  Optional GUI support (PySide6 / Tk)
# ─────────────────────────────────────────────────────────────────────────────
try:
    from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget,
                                   QListWidget, QListWidgetItem, QAbstractItemView,
                                   QLabel, QLineEdit, QCheckBox, QPushButton,
                                   QTextEdit, QGridLayout, QGroupBox,
                                   QVBoxLayout, QMessageBox)
    from PySide6.QtGui  import QIntValidator, QDoubleValidator
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
#  Palette (shared by both GUIs)
# ─────────────────────────────────────────────────────────────────────────────
BG, PANEL, FG   = "#1e1e1e", "#252526", "#f0f0f0"
ACCENT, ENTRY   = "#007acc", "#2d2d2d"

# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────
def detect_encoding(path: str) -> str:
    with open(path, 'rb') as f:
        return chardet.detect(f.read())['encoding'] or 'utf‑8'


# ----------------------------------------------------------------------------
#  TXT → slim CSV  (also returns full‑row metadata for Apple export)
# ----------------------------------------------------------------------------
def convert_playlist_to_csv(txt_file: str,
                            csv_dir: str,
                            max_tracks: int | None = None,
                            top_bottom: str | None = None):
    """
    Returns:
        name, csv_path,
        unique_tracks   – list[(artist,title)]
        unique_rows     – list[dict] (full metadata rows)
        header          – list[str]  (column order)
    """
    name     = os.path.splitext(os.path.basename(txt_file))[0]
    csv_path = os.path.join(csv_dir, f"{name}.csv")

    with open(txt_file, 'r', encoding=detect_encoding(txt_file)) as f:
        reader = csv.DictReader(f, delimiter='\t')
        rows   = list(reader)
        header = reader.fieldnames or []

    # slice (top / bottom)
    if top_bottom:
        letter, num = top_bottom[0].upper(), top_bottom[1:]
        if num.isdigit():
            n = int(num)
            rows = rows[:n] if letter == 'T' else rows[-n:]

    if max_tracks is not None:
        rows = rows[:max_tracks]

    seen, uniq, uniq_rows = set(), [], []
    with open(csv_path, 'w', newline='', encoding='utf‑8') as out:
        w = csv.writer(out); w.writerow(['artist', 'track title'])
        for r in rows:
            key = (r['Artist'], r['Name'])
            if key not in seen:
                seen.add(key); uniq.append(key); uniq_rows.append(r)
                w.writerow(key)

    return name, csv_path, uniq, uniq_rows, header


# ----------------------------------------------------------------------------
#  Load slim CSVs  (shuffle, drop shared if needed)
# ----------------------------------------------------------------------------
def load_csv_playlists(csv_files, disallow_shared, shared_tracks):
    data = {}
    for p in csv_files:
        tracks = [tuple(row) for row in
                  pd.read_csv(p).itertuples(index=False, name=None)]
        if disallow_shared:
            tracks = [t for t in tracks if t not in shared_tracks]
        random.shuffle(tracks)
        data[p] = tracks
    return data


# ----------------------------------------------------------------------------
#  Weighted interleave
# ----------------------------------------------------------------------------
def create_mixed_playlist(pl_tracks, percents, total, max_per_artist):
    picks = {pl: round(total * percents.get(pl, 0)) for pl in pl_tracks}
    diff  = total - sum(picks.values())
    for pl in picks:
        if diff == 0: break
        picks[pl] += 1 if diff > 0 else -1
        diff      += -1 if diff > 0 else 1

    chosen, artist_tot = {pl: [] for pl in pl_tracks}, {}
    for pl, tracks in pl_tracks.items():
        for art, tit in tracks:
            if len(chosen[pl]) == picks[pl]: break
            if max_per_artist and artist_tot.get(art, 0) >= max_per_artist: continue
            chosen[pl].append((art, tit))
            artist_tot[art] = artist_tot.get(art, 0) + 1

    placed = []
    for pl, tracks in chosen.items():
        k = len(tracks)
        if not k: continue
        pos = [total/2] if k == 1 else [i*(total-1)/(k-1) for i in range(k)]
        placed.extend((p,t) for p,t in zip(pos, tracks))

    placed.sort(key=lambda x: x[0])
    return [t for _, t in placed]


# ----------------------------------------------------------------------------
#  Save outputs (csv, txt, full Apple TSV)
# ----------------------------------------------------------------------------
def save_mixed_playlist(mixed, row_map, header):
    base = os.path.join(MIXED_OUTPUT_FOLDER, 'mixed_playlist')
    csv_p, txt_p, apple_p = base+'.csv', base+'.txt', base+'_apple.txt'

    with open(csv_p, 'w', newline='', encoding='utf‑8') as f:
        csv.writer(f).writerows([('artist','track title'), *mixed])

    with open(txt_p, 'w', encoding='utf‑8') as f:
        for art, tit in mixed: f.write(f"{art} - {tit}\n")

    # full Apple TSV
    with open(apple_p, 'w', newline='', encoding='utf‑8') as f:
        w = csv.DictWriter(f, fieldnames=header, delimiter='\t', extrasaction='ignore')
        w.writeheader()
        for key in mixed:
            row = row_map.get(key, {'Name':key[1],'Artist':key[0]})
            w.writerow(row)

    print("✓ Mixed playlist written:")
    print("  ", csv_p)
    print("  ", txt_p)
    print("  ", apple_p)


# ─────────────────────────────────────────────────────────────────────────────
#  CLI driver  (unchanged)
# ─────────────────────────────────────────────────────────────────────────────
def cli():
    txt_files = [os.path.join(INPUT_FOLDER,f) for f in os.listdir(INPUT_FOLDER)
                 if f.lower().endswith('.txt')]
    if not txt_files:
        print("No .txt playlists in 'playlists/'"); return

    print("Available playlists:")
    for i,p in enumerate(txt_files,1): print(f"{i:2d}. {os.path.basename(p)}")
    sel = input("Pick numbers (comma, ENTER=all): ").strip()
    if sel:
        try:
            idx = [int(x) for x in sel.split(',')]
            txt_files = [txt_files[i-1] for i in idx if 1<=i<=len(txt_files)]
        except: print("Ignoring bad input, using all.")

    tb   = input("Top/Bottom slice (T500/B500, ENTER none): ").strip() or None
    mx_s = input("Max tracks per playlist (ENTER all): ").strip()
    max_pl = int(mx_s) if mx_s.isdigit() else None

    csv_paths, row_map, header, shared_ctr = [], {}, None, {}
    for txt in txt_files:
        n,csv_p,uniq,uniq_rows,hdr = convert_playlist_to_csv(txt,CSV_FOLDER,max_pl,tb)
        csv_paths.append(csv_p)
        header = header or hdr
        for k,r in zip(uniq,uniq_rows):
            row_map.setdefault(k,r); shared_ctr[k] = shared_ctr.get(k,0)+1
    shared = {k for k,c in shared_ctr.items() if c>1}

    perc, default = {}, 100/len(csv_paths)
    print(f"Percent per playlist (ENTER={default:.2f}):")
    for p in csv_paths:
        base = os.path.splitext(os.path.basename(p))[0]
        v = input(f"  {base}: ").strip()
        perc[p]=float(v) if v else default
    tot=sum(perc.values()) or 1
    for k in perc: perc[k]/=tot

    n_tot = int(input("Total mix size (default 1000): ").strip() or 1000)
    mpa   = int(input("Max tracks per artist (default 5): ").strip() or 5)
    dis   = input("Allow shared tracks? (y/N): ").strip().lower()=='n'

    tracks = load_csv_playlists(csv_paths, dis, shared)
    mixed  = create_mixed_playlist(tracks, perc, n_tot, mpa)
    save_mixed_playlist(mixed, row_map, header)
    print(f"Done – {len(mixed)} tracks.")


# ─────────────────────────────────────────────────────────────────────────────
#  Tkinter GUI  (styled)
# ─────────────────────────────────────────────────────────────────────────────
def tk_main():
    root = tk.Tk(); root.title("Apple Playlist Mixer"); root.configure(bg=BG)
    root.geometry("1000x600")

    # --- style tweaks ---
    style = ttk.Style(root); style.theme_use('clam')
    style.configure('.', background=BG, foreground=FG)
    style.configure('TButton', background=ACCENT, foreground='white',
                    borderwidth=0, padding=6)
    style.map('TButton', background=[('active', '#0892d0')])
    style.configure('TEntry', fieldbackground=ENTRY, foreground=FG,
                    bordercolor='#3c3c3c')

    txt_files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith('.txt')]

    # ---- Playlist list ------------------------------------------------------
    lb = tk.Listbox(root, selectmode='multiple', bg=PANEL, fg=FG,
                    selectbackground=ACCENT, highlightthickness=0)
    for f in txt_files: lb.insert('end',f); lb.selection_set(0,'end')
    lb.grid(row=0,column=0,rowspan=4,sticky='ns',padx=10,pady=10)

    # ---- Controls -----------------------------------------------------------
    v_tb, v_maxpl = tk.StringVar(), tk.StringVar()
    v_total, v_mpa = tk.StringVar(value='1000'), tk.StringVar(value='5')
    v_disallow = tk.BooleanVar(value=False)

    frm = ttk.Frame(root); frm.grid(row=0,column=1,sticky='nw',padx=10,pady=10)
    ttk.Label(frm,text="Top/Bottom (T500/B500):").grid(row=0,column=0,sticky='w')
    ttk.Entry(frm,textvariable=v_tb,width=12).grid(row=0,column=1)
    ttk.Label(frm,text="Max tracks per playlist:").grid(row=1,column=0,sticky='w')
    ttk.Entry(frm,textvariable=v_maxpl,width=12).grid(row=1,column=1)

    prm = ttk.Frame(root); prm.grid(row=1,column=1,sticky='nw',padx=10)
    ttk.Label(prm,text="Total tracks:").grid(row=0,column=0,sticky='w')
    ttk.Entry(prm,textvariable=v_total,width=8).grid(row=0,column=1)
    ttk.Label(prm,text="Max per artist:").grid(row=1,column=0,sticky='w')
    ttk.Entry(prm,textvariable=v_mpa,width=8).grid(row=1,column=1)
    ttk.Checkbutton(prm,text="Disallow shared tracks",variable=v_disallow)\
        .grid(row=2,column=0,columnspan=2,sticky='w',pady=4)

    # ---- Percent widgets & refresh -----------------------------------------
    pct_vars, pct_frame = {}, ttk.Frame(root)
    pct_frame.grid(row=2,column=1,sticky='nw',padx=10,pady=10)
    def refresh_pct(_=None):
        for w in pct_frame.winfo_children(): w.destroy()
        pct_vars.clear()
        sel = lb.curselection()
        default = 100/len(sel) if sel else 0
        for r,i in enumerate(sel):
            name=txt_files[i]
            ttk.Label(pct_frame,text=name).grid(row=r,column=0,sticky='w')
            var=tk.StringVar(value=f"{default:.2f}")
            pct_vars[name]=var
            ttk.Entry(pct_frame,textvariable=var,width=6).grid(row=r,column=1)
    lb.bind("<<ListboxSelect>>", refresh_pct); refresh_pct()

    # ---- Log ---------------------------------------------------------------
    log = tk.Text(root,bg=PANEL,fg=FG,width=60,height=26,
                  highlightthickness=0); log.grid(row=0,column=2,rowspan=4,padx=10,pady=10)
    def wlog(msg): log.insert('end',msg+'\n'); log.see('end')

    # ---- Run button --------------------------------------------------------
    def run():
        log.delete('1.0','end')
        sel = lb.curselection()
        if not sel: messagebox.showerror("Error","Select at least one playlist."); return

        tb = v_tb.get() or None
        mx = int(v_maxpl.get()) if v_maxpl.get().isdigit() else None

        csv_paths, row_map, hdr, shared_ctr = [], {}, None, {}
        for i in sel:
            txt = os.path.join(INPUT_FOLDER,txt_files[i])
            n,csv_p,uniq,uniq_rows,h = convert_playlist_to_csv(txt,CSV_FOLDER,mx,tb)
            wlog(f"Converted {n}")
            csv_paths.append(csv_p); hdr = hdr or h
            for k,r in zip(uniq,uniq_rows):
                row_map.setdefault(k,r); shared_ctr[k]=shared_ctr.get(k,0)+1
        shared = {k for k,c in shared_ctr.items() if c>1}

        pct={}
        for name,var in pct_vars.items():
            v=float(var.get() or 0)
            csv_p=os.path.join(CSV_FOLDER,os.path.splitext(name)[0]+'.csv')
            pct[csv_p]=v
        tot=sum(pct.values()) or 1
        for k in pct: pct[k]/=tot

        total=int(v_total.get() or 1000)
        mpa  =int(v_mpa.get() or 5)
        dis  =v_disallow.get()

        tracks = load_csv_playlists(csv_paths, dis, shared)
        mixed  = create_mixed_playlist(tracks, pct, total, mpa)
        save_mixed_playlist(mixed,row_map,hdr)
        wlog(f"✓ Mixed playlist with {len(mixed)} tracks.")
        messagebox.showinfo("Done",f"{len(mixed)} tracks created.")

    ttk.Button(root,text="Mix Playlists",command=run)\
        .grid(row=3,column=1,pady=12,sticky='ew')
    root.mainloop()


# ─────────────────────────────────────────────────────────────────────────────
#  PySide6 GUI  (styled)
# ─────────────────────────────────────────────────────────────────────────────
def qt_main():
    app=QApplication(sys.argv)
    app.setStyleSheet(f"""
        QWidget       {{ background:{BG}; color:{FG}; font-family:'Helvetica Neue'; }}
        QListWidget   {{ background:{PANEL}; border:0; }}
        QListWidget::item:selected {{ background:{ACCENT}; color:white; }}
        QLineEdit, QTextEdit {{
            background:{ENTRY}; border:1px solid #3c3c3c; border-radius:4px; padding:4px;
        }}
        QPushButton {{
            background:{ACCENT}; color:white; border:0; border-radius:4px; padding:6px 12px;
        }}
        QPushButton:hover {{ background:#0892d0; }}
        QGroupBox {{ border:1px solid #3c3c3c; border-radius:6px; margin-top:6px; }}
        QGroupBox:title {{ subcontrol-origin: margin; left:10px; padding:0 4px; }}
    """)
    win=QMainWindow(); win.setWindowTitle("Apple Playlist Mixer"); win.resize(1000,600)
    central=QWidget(); win.setCentralWidget(central); lay=QGridLayout(central)

    txt_files=sorted([f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith('.txt')])
    lb=QListWidget(); lb.setSelectionMode(QAbstractItemView.MultiSelection)
    for f in txt_files: lb.addItem(QListWidgetItem(f)); lb.selectAll()
    lay.addWidget(lb,0,0,4,1)

    le_tb, le_maxpl = QLineEdit(), QLineEdit(); le_maxpl.setValidator(QIntValidator())
    le_tot, le_mpa  = QLineEdit("1000"), QLineEdit("5")
    le_tot.setValidator(QIntValidator()); le_mpa.setValidator(QIntValidator())
    cb_dis  = QCheckBox("Disallow shared tracks")

    def group(title,*rows):
        g=QGroupBox(title); L=QGridLayout(g)
        for r,(lbl,wdg) in enumerate(rows):
            if lbl: L.addWidget(QLabel(lbl),r,0)
            L.addWidget(wdg,r,1)
        return g

    lay.addWidget(group("Options",
                        ("Top/Bottom:",le_tb),
                        ("Max tracks per playlist:",le_maxpl)),0,1)
    lay.addWidget(group("Parameters",
                        ("Total tracks:",le_tot),
                        ("Max per artist:",le_mpa),
                        ("",cb_dis)),1,1)

    pct_grp=QGroupBox("Percentages"); pct_lay=QGridLayout(pct_grp); pct_edits={}
    def refresh():
        for i in reversed(range(pct_lay.count())):
            pct_lay.itemAt(i).widget().deleteLater()
        pct_edits.clear(); sel=lb.selectedItems()
        default=100/len(sel) if sel else 0
        for r,it in enumerate(sel):
            pct_lay.addWidget(QLabel(it.text()),r,0)
            e=QLineEdit(f"{default:.2f}"); e.setValidator(QDoubleValidator(0,100,2))
            pct_edits[it.text()]=e; pct_lay.addWidget(e,r,1)
    lb.itemSelectionChanged.connect(refresh); refresh()
    lay.addWidget(pct_grp,2,1)

    log=QTextEdit(); log.setReadOnly(True); lay.addWidget(log,0,2,3,1)
    def wlog(m): log.append(m)

    btn=QPushButton("Mix Playlists"); lay.addWidget(btn,3,1)
    def run():
        sel=lb.selectedItems()
        if not sel:
            QMessageBox.critical(win,"Error","Select playlists"); return
        tb=le_tb.text() or None
        mx=int(le_maxpl.text()) if le_maxpl.text().isdigit() else None

        csv_paths,row_map,hdr,shared_ctr=[],{},None,{}
        for it in sel:
            txt=os.path.join(INPUT_FOLDER,it.text())
            n,csv_p,uniq,uniq_rows,h=convert_playlist_to_csv(txt,CSV_FOLDER,mx,tb)
            wlog(f"Converted {n}")
            csv_paths.append(csv_p); hdr=hdr or h
            for k,r in zip(uniq,uniq_rows):
                row_map.setdefault(k,r); shared_ctr[k]=shared_ctr.get(k,0)+1
        shared={k for k,c in shared_ctr.items() if c>1}

        pct={}
        for name,edit in pct_edits.items():
            val=float(edit.text() or 0)
            pct[os.path.join(CSV_FOLDER,os.path.splitext(name)[0]+'.csv')]=val
        tot=sum(pct.values()) or 1
        for k in pct: pct[k]/=tot

        n_tot=int(le_tot.text() or 1000)
        mpa=int(le_mpa.text() or 5)
        dis=cb_dis.isChecked()

        tracks=load_csv_playlists(csv_paths,dis,shared)
        mixed=create_mixed_playlist(tracks,pct,n_tot,mpa)
        save_mixed_playlist(mixed,row_map,hdr)
        wlog(f"✓ Mixed playlist {len(mixed)} tracks")
        QMessageBox.information(win,"Done",f"{len(mixed)} tracks.")
    btn.clicked.connect(run)

    win.show(); app.exec()


# ─────────────────────────────────────────────────────────────────────────────
#  Entrypoint
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if "--cli" in sys.argv:
        cli()
    elif QT_AVAILABLE:
        try:
            qt_main()
        except Exception as e:
            print("Qt GUI error, falling back to CLI:", e); cli()
    elif TK_AVAILABLE:
        try:
            tk_main()
        except Exception as e:
            print("Tk GUI error, falling back to CLI:", e); cli()
    else:
        cli()
