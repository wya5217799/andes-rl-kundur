"""R281 smoke: verify ANDES EIG works on kundur_full.xlsx in WSL."""
import numpy as np
import andes

print("andes", andes.__version__)
ss = andes.load(andes.get_case("kundur/kundur_full.xlsx"), default_config=True, setup=True)
print("setup ok, buses:", len(ss.Bus.idx.v))
ss.PFlow.run()
print("pflow converged:", ss.PFlow.converged)
ss.EIG.run()
print("eig ok, n states:", ss.EIG.N)
ev = np.asarray(ss.EIG.mu)
print("n eig:", len(ev))
neg = ev[ev.real < 0]
w = np.abs(neg.imag) / (2 * np.pi)
damp = -neg.real / np.abs(neg)
osc = neg[w > 0.05]
order = np.argsort(np.abs(osc.imag))[:10]
for i in order:
    print(f"  mode: f={abs(osc[i].imag)/2/np.pi:.3f} Hz  damp={-osc[i].real/abs(osc[i]):.4f}")
