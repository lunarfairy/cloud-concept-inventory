
import json, sys, time, torch, numpy as np
from transformers import AutoTokenizer, AutoModelForCausalLM
torch.set_num_threads(int(sys.argv[1]))
B=json.load(open("data/banks.json")); PRE=B['PREAMBLE_R4']; LET="ABCD"
done=set()
try:
    for l in open("data/llm/local_scores_r4.jsonl"):
        r=json.loads(l); done.add((r['model'],r['bank'],r['cond'],r['item']))
except FileNotFoundError: pass
out=open("data/llm/local_scores_r4.jsonl","a")
for mdir in sys.argv[2:]:
    name=mdir.split("/")[-1]
    tok=AutoTokenizer.from_pretrained(mdir); tok.padding_side='left'
    if tok.pad_token is None: tok.pad_token=tok.eos_token
    model=AutoModelForCausalLM.from_pretrained(mdir, dtype=torch.float32); model.eval()
    ids=[tok.encode(x, add_special_tokens=False)[-1] for x in LET]
    ids_sp=[tok.encode(" "+x, add_special_tokens=False)[-1] for x in LET]
    t0=time.time()
    for bank, cond in [('R4','full'),('R4','optonly')]:
        for it in B[bank]:
            if (name,bank,cond,it['id']) in done: continue
            prompts=[]; perms=[]
            for shift in range(4):
                perm=[(j+shift)%4 for j in range(4)]; perms.append(perm)
                stem=it['stem'] if cond=='full' else "(question text withheld; choose the option most likely to be correct)"
                body=PRE+"\nQuestion: "+stem+"\n"+"\n".join(f"{LET[j]}. {it['options'][perm[j]]['text']}" for j in range(4))+"\nAnswer with a single letter."
                prompts.append(tok.apply_chat_template([{"role":"user","content":body}], tokenize=False, add_generation_prompt=True)+"Answer: ")
            enc=tok(prompts, return_tensors="pt", padding=True)
            with torch.no_grad():
                lg=model(**enc, logits_to_keep=1).logits[:,-1]
            lp=torch.log_softmax(lg.float(),-1)
            probs=np.zeros(4)
            for b in range(4):
                pl=torch.logsumexp(torch.stack([lp[b,ids],lp[b,ids_sp]]),0).exp().numpy(); pl=pl/pl.sum()
                for j in range(4): probs[perms[b][j]]+=pl[j]/4
            out.write(json.dumps(dict(model=name,bank=bank,cond=cond,item=it['id'],probs=dict(zip(LET,probs.round(5).tolist())),key=it['key']))+"\n"); out.flush()
    print(name, "done", round(time.time()-t0), "s", flush=True)
