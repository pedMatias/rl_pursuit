#!/usr/bin/env python

# NEW THOUGHTS: USE THE PDF BACKEND, then use "pdftops -eps filename.pdf" to convert it to an eps - this seems to work better right now - 8/23/12
# 9/28/12 - USE PDF backend, reinstall the normal version of xpdf, via
#  sudo apt-get install libpoppler-glib6 libpoppler-qt4-3 libpoppler13 poppler-utils python-poppler libpoppler-glib4 xpdf --reinstall
# THEN, change the backend to use thicker lines, hack /usr/lib/pymodules/python2.7/matplotlib/backends/backend_pdf.py
#   change line ~1065 from "self.output(0.1,Op.setlinewidth)" to "self.output(1.0,Op.setlinewidth)"

# OLD THOUGHTS:
# NOTE: for the PS backend to work correctly, you may need to install a better version of xpdf (the one in ubuntu 11.10 seems to suck), try this: http://ctan.math.utah.edu/ctan/tex-archive/support/xpdf/xpdfbin-linux-3.03.tar.gz
# NOTE: for better hatching, hack /usr/lib/pymodules/python2.7/matplotlib/backends/backend_ps.py
#  change line: "0 setlinewidth" to "1 setlinewidth"


import sys, numpy
import matplotlib.pyplot as plt

class Options:
  pass

def parseOptions(dest,defaults,options,labelForErrors = None):
  if labelForErrors is None:
    outputLabel = ''
  else:
    outputLabel = '(%s)' % labelForErrors
  for key in options.iterkeys():
    if key not in defaults:
      print >>sys.stderr,'Unknown option given to parseOptions%s: %s' % (outputLabel,key)
      sys.exit(11)
  for key in defaults.iterkeys():
    if key in options:
      val = options[key]
    else:
      val = defaults[key]
    dest.__dict__[key] = val

def getAxisBounds(values,errors,yMinFixed,xOffset,xs):
  if errors is None:
    vals = values
  else:
    vals =  [v+e for v,e in zip(values,errors)]
    vals += [v-e for v,e in zip(values,errors)]
  yMin = min(vals)
  yMax = max(vals)
  if yMinFixed is not None:
    yMin = yMinFixed
  yFudge = (yMax - yMin) * 0.1
  yMin -= yFudge
  yMax += yFudge
  xFudge = 0.1 - xOffset
  if xs is None:
    xMin = -xFudge
    xMax = len(values) - xFudge
  else:
    xMin = min(xs) - xFudge
    xMax = max(xs) + 1 - xFudge
  if yMinFixed is not None:
    yMin = yMinFixed
  return [xMin,xMax,yMin,yMax]

def setParams(options):
  fontSize = options.fontSize
  tickSize = fontSize

  params = {'backend': 'PS','axes.labelsize': fontSize,'text.fontsize': fontSize,'legend.fontsize': fontSize,'xtick.labelsize': tickSize,'ytick.labelsize': tickSize,'text.usetex': True, 'ps.usedistiller': 'xpdf'}
  plt.rcParams.update(params)

def makeLegendOnly(options,filename,lines):
  setParams(options)
  plt.figure()
  plt.axis('off')
  plt.legend(lines,options.labels)

  if filename is None:
    plt.show()
  else:
    plt.savefig(filename,format='pdf',bbox_inches='tight',pad_inches=0.1)

def makeBarGraph(values,options):
  setParams(options)
  xOffset = -0.4

  plt.figure()
  bounds = getAxisBounds(values,options.errors,options.yMinFixed,xOffset,options.xs)
  if options.logY:
    plt.yscale('log')
  else:
    plt.axis(bounds)
  lines = []
  for x,v in enumerate(values):
    styleInd = options.styleInds[x]
    if options.errors is None:
      kwargs = {}
    else:
      kwargs = {'yerr':options.errors[x],'ecolor':'black'}
    
    if options.xs is not None:
      xval = options.xs[x]
    else:
      xval = x

    if options.logY and (v < 1e-99):
      print 'warinng: value too low, skipping %i' % x
      continue
    if x >= len(options.labels):
      print 'warning: skipping label %i' % x
    else:
      kwargs['label'] = options.labels[x]
    
    line = plt.bar(xval+xOffset,v,color=options.colors[styleInd],hatch=options.styles[styleInd],**kwargs)
    lines.append(line)
  if options.legendLoc is not None:
    plt.legend(loc=options.legendLoc)

  plt.ylabel(options.ylabel)
  plt.xlabel(options.xlabel)
  plt.title(options.title)
  
  if options.logY:
    orig = list(plt.axis())
    orig[0] = bounds[0]
    orig[1] = bounds[1]
    if options.yaxisFactors is not None:
      orig[2] *= options.yaxisFactors[0]
      orig[3] *= options.yaxisFactors[1]
    plt.axis(orig)

  if options.callback is not None:
    options.callback(lines)
  plt.xticks(options.xtickLocs,options.xtickLabels)
  if options.filename is None:
    plt.show()
  else:
    plt.savefig(options.filename,format='pdf',bbox_inches='tight',pad_inches=0.1)
  return lines

def readFile(filename):
  data = numpy.loadtxt(filename,dtype=float,delimiter=',')
  origLen = data.shape[0]
  data = data[~numpy.isnan(data).any(1)]
  if data.shape[0] != origLen:
    print 'WARNING: removed nans from %s, resulting in %i episodes' % (filename,data.shape[0])
  # should be of form: jobNum, steps
  assert(data.shape[1] == 2),'Two columns expected in data'
  return data[:,1]

def main(filenames,options):
  bars = []
  for filename in filenames:
    vals = readFile(filename)
    bars.append(vals.mean())
    if options.errors is not None:
      options.errors.append(numpy.std(vals) / numpy.sqrt(len(vals)))
  return makeBarGraph(bars,options)

def getMainOpts(**kwargs):
  defaults = {
    'filename': None,
    'yMinFixed': None,
    'labels': None,
    'errors': None,
    'colors': ['b','r','g','c','m','y','k'],
    'styles': ['.','|','-','/','\\','+','x','o','0','*'],
    'legendLoc': 'best',
    'ylabel': '',
    'xlabel': '',
    'title': '',
    'fontSize': 24,
    'styleInds': None,
    'xtickLocs': [],
    'xtickLabels': [],
    'logY': False,
    'xs': None,
    'callback':None,
    'yaxisFactors': None
  }
  options = Options()
  parseOptions(options,defaults,kwargs,'Main')
  if options.styleInds is None:
    options.styleInds = range(10)
  return options

if __name__ == '__main__':
  args = sys.argv[1:]
  assert(len(args) > 0)
  options = getMainOpts(labels=args)
  main(args,options)
