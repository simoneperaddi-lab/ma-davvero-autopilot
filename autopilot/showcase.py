"""Three actual NASA-backed films, no Instagram import or credentials."""
import argparse
import json
from pathlib import Path
from autopilot.documentaries import STORIES, verify
from autopilot.cinema_render import render


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=Path('data/cinema-showcase'));parser.add_argument('--story',choices=list(STORIES));args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    for key in ([args.story] if args.story else STORIES):
        target=args.output/key
        fact,asset=verify(key,target/'sources')
        render(fact,target,asset=asset)
        print(key, json.loads((target/'technical-report.json').read_text()),flush=True)
    (args.output/'index.html').write_text('<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>MA DAVVERO? — visione editoriale</title><style>body{background:#080d15;color:#eee;font:18px system-ui;margin:24px}section{display:inline-block;vertical-align:top;width:min(100%,380px);margin:12px}video,img{width:100%}a{color:#e3c091}</style><h1>MA DAVVERO?</h1><p>Tre film, nessuna pubblicazione. Aprire questa pagina dopo aver estratto lo ZIP.</p>'+''.join(f'<section><h2>{s["title"]}</h2><video controls playsinline preload="metadata" poster="{k}/frames/01.jpg" src="{k}/reel.mp4"></video><p><a href="{k}/caption.txt">Caption e fonti</a> · <a href="{k}/evidence.json">Provenienza</a> · <a href="{k}/technical-report.json">Controlli</a></p><img src="{k}/contact-sheet.jpg" alt="Otto fotogrammi del montaggio"></section>' for k,s in STORIES.items()),encoding='utf-8')

if __name__=='__main__':main()
