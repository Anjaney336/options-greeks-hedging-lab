import math,unittest
from pricing import greeks,implied_vol
from hedging import hedge,path
class PricingTests(unittest.TestCase):
 def test_known_price(self):self.assertAlmostEqual(greeks(100,100,1,.05,.2)['price'],10.450583572,places=8)
 def test_parity(self):
  for s in [70,100,130]:self.assertAlmostEqual(greeks(s,100,.5,.03,.25)['price']-greeks(s,100,.5,.03,.25,'put')['price'],s-100*math.exp(-.015),places=10)
 def test_delta(self):
  h=.001;g=greeks(100,105,.4,.03,.3);self.assertAlmostEqual(g['delta'],(greeks(100+h,105,.4,.03,.3)['price']-greeks(100-h,105,.4,.03,.3)['price'])/(2*h),places=7)
 def test_gamma(self):
  h=.01;f=lambda s:greeks(s,105,.4,.03,.3)['price'];self.assertAlmostEqual(greeks(100,105,.4,.03,.3)['gamma'],(f(100+h)-2*f(100)+f(100-h))/h**2,places=7)
 def test_vega(self):
  h=1e-5;f=lambda v:greeks(100,105,.4,.03,v)['price'];self.assertAlmostEqual(greeks(100,105,.4,.03,.3)['vega'],(f(.3+h)-f(.3-h))/(2*h),places=6)
 def test_theta(self):
  h=1e-5;f=lambda t:greeks(100,105,t,.03,.3)['price'];self.assertAlmostEqual(greeks(100,105,.4,.03,.3)['theta'],-(f(.4+h)-f(.4-h))/(2*h),places=6)
 def test_rho(self):
  h=1e-5;f=lambda r:greeks(100,105,.4,r,.3)['price'];self.assertAlmostEqual(greeks(100,105,.4,.03,.3)['rho'],(f(.03+h)-f(.03-h))/(2*h),places=6)
 def test_expiry(self):
  self.assertEqual(greeks(120,100,0,0,.2)['price'],20);self.assertEqual(greeks(90,100,0,0,.2,'put')['price'],10)
 def test_iv_roundtrip(self):
  for v in [.1,.25,.7]:self.assertAlmostEqual(implied_vol(greeks(100,100,.5,.02,v)['price'],100,100,.5,.02),v,places=9)
 def test_iv_invalid(self):
  with self.assertRaises(ValueError):implied_vol(200,100,100,.5,.02)
 def test_parameter_rejection(self):
  with self.assertRaises(ValueError):greeks(-1,100,.5,.02,.2)
class HedgeTests(unittest.TestCase):
 def test_cash_nohedge_identity(self):
  p=[100,110,105];v=greeks(100,100,2/252,.02,.25)['price'];x=hedge(p,'none',fee_bps=0)
  self.assertAlmostEqual(x['terminal_pnl'],5-v*math.exp(.02*2/252))
 def test_self_financing(self):
  for seed in range(30):
   for policy in ['none','daily','band']:self.assertAlmostEqual(hedge(path(seed,'jump'),policy)['bridge_residual'],0,places=9)
 def test_terminal_flat(self):self.assertEqual(hedge(path(4))['ledger'][-1]['units'],0)
 def test_cost_monotonicity(self):self.assertLess(hedge(path(3),fee_bps=10)['terminal_pnl'],hedge(path(3),fee_bps=0)['terminal_pnl'])
 def test_band_zero_equals_daily(self):self.assertEqual(hedge(path(2),'band',band=0)['terminal_pnl'],hedge(path(2),'daily')['terminal_pnl'])
 def test_future_mutation(self):
  a=path(2);b=a.copy();b[-1]*=1.5
  self.assertEqual(hedge(a)['ledger'][:30],hedge(b)['ledger'][:30])
 def test_greek_attribution_identity(self):
  for row in hedge(path(9,'jump'))['ledger']:self.assertAlmostEqual(row['option_change'],sum(row[k] for k in ['delta_component','gamma_component','theta_component','approximation_residual']),places=10)
 def test_reproducibility(self):self.assertEqual(path(12),path(12))
 def test_bad_path(self):
  with self.assertRaises(ValueError):hedge([100,float('nan')])
if __name__=='__main__':unittest.main()

