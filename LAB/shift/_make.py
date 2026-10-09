import sys,glob,librosa,numpy as np,soundfile as sf
from concurrent.futures import ProcessPoolExecutor
D,S=sys.argv[1],sys.argv[2]
VAR={"V3":(1,0.98)}
def job(a):
    f,t,kind,v=a; st,r=VAR[v]
    y,sr=librosa.load(f,sr=44100,mono=True)
    if r!=1.0: y=librosa.effects.time_stretch(y,rate=r)
    y=librosa.effects.pitch_shift(y,sr=sr,n_steps=st,res_type="soxr_hq")
    out=f"{S}/{t}_{kind}_{v}.wav"; sf.write(out,np.stack([y,y],1),sr); return out
if __name__=="__main__":
    tasks=[]
    for p,t in [("1_","NP"),("2_","PR")]:
        for kind,pat in [("vocals","Vocals"),("inst","Instrumental")]:
            f=glob.glob(D+f"/{p}*{pat}*.wav")[0]
            for v in VAR: tasks.append((f,t,kind,v))
    with ProcessPoolExecutor(4) as ex:
        for o in ex.map(job,tasks): print("ok",o)
