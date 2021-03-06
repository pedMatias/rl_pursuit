#!/usr/bin/env python

from PyQt4 import QtGui, QtCore
import json, re, types

def json_minify(json,strip_space=True):
  # taken from https://github.com/getify/JSON.minify.git
  tokenizer=re.compile('"|(/\*)|(\*/)|(//)|\n|\r')
  in_string = False
  in_multiline_comment = False
  in_singleline_comment = False
  
  new_str = []
  from_index = 0 # from is a keyword in Python
  
  for match in re.finditer(tokenizer,json):
      if not in_multiline_comment and not in_singleline_comment:
          tmp2 = json[from_index:match.start()]
          if not in_string and strip_space:
              tmp2 = re.sub('[ \t\n\r]*','',tmp2) # replace only white space defined in standard
          new_str.append(tmp2)
          
      from_index = match.end()
      
      if match.group() == '"' and not in_multiline_comment and not in_singleline_comment:
          escaped = re.search('(\\\\)*$',json[:match.start()])
          if not in_string or escaped is None or len(escaped.group()) % 2 == 0:
              # start of string with ", or unescaped " character found to end string
              in_string = not in_string
          from_index -= 1 # include " character in next catch
          
      elif match.group() == '/*' and not in_string and not in_multiline_comment and not in_singleline_comment:
          in_multiline_comment = True
      elif match.group() == '*/' and not in_string and in_multiline_comment and not in_singleline_comment:
          in_multiline_comment = False
      elif match.group() == '//' and not in_string and not in_multiline_comment and not in_singleline_comment:
          in_singleline_comment = True
      elif (match.group() == '\n' or match.group() == '\r') and not in_string and not in_multiline_comment and in_singleline_comment:
          in_singleline_comment = False
      elif not in_multiline_comment and not in_singleline_comment and (
           match.group() not in ['\n','\r',' ','\t'] or not strip_space):
              new_str.append(match.group())
  
  new_str.append(json[from_index:])
  return ''.join(new_str)


class TreeItem(QtGui.QTreeWidgetItem):
  def __init__(self,parent,vals):
    tempVals = list(vals)
    if vals[1] is None:
      tempVals[1] = ''
    super(TreeItem, self).__init__(parent,map(str,tempVals))
    self.dataType = type(vals[1])
    if vals[1] != None:
      self.setFlags(QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled)
    self.setExpanded(True)

  def getVal(self):
    if self.dataType is bool:
      return self.text(1) in ['True','true','T','t']
    return self.dataType(self.text(1))

class DependentItem(TreeItem):
  def __init__(self,parent,dependency,depVals,vals):
    super(DependentItem, self).__init__(parent,vals)
    self.dependency = dependency
    if type(depVals) is list:
      self.depVals = depVals
    else:
      self.depVals = [depVals]
    self.setView()

  def setView(self):
    if not(self.dependency.isHidden()) and (self.dependency.text(1) in self.depVals):
      self.setHidden(False)
    else:
      self.setHidden(True)

class Tree(object):
  def __init__(self):
    self.tree = QtGui.QTreeWidget()
    self.tree.setColumnCount(2)
    self.tree.setHeaderLabels(["Name","Val"])
    self.tree.header().resizeSection(0,300)
    self.tree.show()
    self.depOptions = []
    self.models = {}
    self.tree.itemChanged.connect(self.setViews)
    self.tree.itemClicked.connect(self.click)

  def click(self,x,col):
    if x in self.models:
      self.models[x] = not(self.models[x])
      disable = not(self.models[x])
      if disable:
        bg = QtGui.QColor('black')
        fg = QtGui.QColor('white')
      else:
        bg = QtGui.QColor('white')
        fg = QtGui.QColor('black')
      x.setBackground(0,bg)
      x.setBackground(1,bg)
      x.setForeground(0,fg)
      x.setForeground(1,fg)
      x.setSelected(False)

  def setViews(self,x):
    for opt in self.depOptions:
      try:
        opt.setView()
      except RuntimeError:
        pass
 
  def addOption(self,vals,parent=None,parent2=None):
    if parent2 is not None:
      vals = [vals,parent]
      parent = parent2
    elif type(parent) not in [QtGui.QTreeWidget,QtGui.QTreeWidgetItem,None]:
      vals = [vals,parent]
      parent = None
    if parent is None:
      parent = self.tree
    temp = TreeItem(parent,vals)
    return temp
  
  def addDependentOption(self,dependency,depVal,vals,parent=None):
    if parent is None:
      parent = self.tree
    temp = DependentItem(parent,dependency,depVal,vals)
    self.depOptions.append(temp)
    return temp

  def populateJson(self,val,item):
    if item.isHidden():
      return
    if (item in self.models) and not(self.models[item]):
      return
    key = str(item.text(0))
    if item.dataType is types.NoneType:
      val[key] = {}
      for i in range(item.childCount()):
        self.populateJson(val[key],item.child(i))
      if item.text(0) == 'models':
        val[key] = val[key].values()
    else:
      val[key] = item.getVal()

  def output(self,outFile=None):
    self.json = {}
    for i in range(self.tree.topLevelItemCount()):
      self.populateJson(self.json,self.tree.topLevelItem(i))
    if outFile is None:
      print json.dumps(self.json,indent=2)
    else:
      with open(outFile,'w') as f:
        json.dump(self.json,f,indent=2)
  
  def read(self,filename):
    with open(filename,'r') as f:
      contents = f.read()
      contents = json_minify(contents)
      defaults = json.loads(contents)
    for key,val in defaults.iteritems():
      for i in range(self.tree.topLevelItemCount()):
        item = self.tree.topLevelItem(i)
        if item.text(0) == key:
          self.readJson(item,key,val)
          break
      else:
        if key not in ['trials','trialsPerJob','save']:
          import sys
          print >>sys.stderr,'ERROR: unknown key: %s' % key
          sys.exit(2)
    self.setViews(None)

  def readJson(self,item,key,val):
    if key == 'models':
      for model in self.models:
        model.parent().removeChild(model)
      self.models = {}
      for m in val:
        k = m['desc']
        child = self.options.addModel(k,'UNKNOWN','UNKNOWN')
        self.readJson(child,k,m)
        #print m['desc']
        #self.models[m['desc']]

        #print model
      #self.models.
      # handle specially
      return

    if type(val) in [unicode,int,float,bool,str]:
      item.setText(1,str(val))
      #print 'setting:',key,val
    elif type(val) is dict:
      for k,v in val.iteritems():
        for i in range(item.childCount()):
          child = item.child(i)
          if child.text(0) == k:
            self.readJson(child,k,v)
            break
        else:
          import sys
          print >>sys.stderr,'ERROR: unknown key: %s' % k
          sys.exit(2)
    else:
      import sys
      print >>sys.stderr,'ERROR: unknown type: %s for key %s' % (type(val),key)
      sys.exit(3)

class Options(object):
  def __init__(self,tree):
    self.tree = tree
    self.setupWorld()
    self.setupPlanner()

  def addOption(self,*args,**kwargs):
    return self.tree.addOption(*args,**kwargs)
  
  def addDependentOption(self,*args,**kwargs):
    return self.tree.addDependentOption(*args,**kwargs)

  def setupWorld(self):
    self.addOption('centerPrey',True)
    self.addOption('width',20)
    self.addOption('height',20)
    self.setupVerbosity()

    self.setupAgent('prey','random')
    self.adhoc = self.setupAgent('adhoc','mcts')
    self.setupAgent('predator','student')

  def setupVerbosity(self):
    x = self.addOption('verbosity',None)
    self.addOption('description',True,x)
    self.addOption('observation',False,x)
    self.addOption('stepsPerEpisode',False,x)
    self.addOption('stepsPerTrial',False,x)
    self.addOption('summary',True,x)
    x.setExpanded(False)

  def setupAgent(self,agent,agentType,parent=None):
    a = self.addOption(agent,agentType,parent)
    ao = self.addDependentOption(a,['student','dt','dummy','classifier'],[agent + 'Options',None],parent)

    self.addDependentOption(a,'classifier',['dataPerStudent',False],parent)
    self.addDependentOption(a,'classifier',['modelPerStudent',False],parent)
    self.addDependentOption(a,'classifier',['includeCurrentStudent',True],parent)

    self.addDependentOption(a,'student',['student','data/students.txt'],ao)
    self.addDependentOption(a,'classifier',['shared',True],ao)
    self.addDependentOption(a,'classifier',['caching',False],ao)
    self.addDependentOption(a,'classifier',['filename',''],ao)
    self.addDependentOption(a,'classifier',['data','data/dt/ra-20x20-centerPrey-myActionHistory-5000/train/$(MODEL_STUDENT).arff'],ao)
    self.addDependentOption(a,'classifier',['trainingPeriod',-1],ao)
    self.addDependentOption(a,'classifier',['trainIncremental',True],ao)
    self.setupClassifier(a,ao)
    self.addDependentOption(a,'dummy',['action',0],ao)
    return a

  def setupClassifier(self,a,ao,remainingDepth=2):
    boosters = ['adaboost','tradaboost','adaboostprime','twostagetradaboost','trbagg']

    if a is None:
      t = self.addOption('type','dt',ao)
    else:
      t = self.addDependentOption(a,'classifier',['type','dt'],ao)

    self.addDependentOption(t,['lsvm','svm'],['maxNumInstances',630000],ao)
    self.addDependentOption(t,'lsvm',['solverType',0],ao)
    self.addDependentOption(t,'dt',['maxDepth',-1],ao)
    self.addDependentOption(t,'dt',['minInstances',2],ao)
    self.addDependentOption(t,'dt',['minGain',0.0001],ao)
    self.addDependentOption(t,'weka',['wekaOptions','weka.classifiers.trees.J48'],ao)
    self.addDependentOption(t,boosters,['maxBoostingIterations',10],ao)
    self.addDependentOption(t,'twostagetradaboost',['numFolds',5],ao)
    self.addDependentOption(t,'twostagetradaboost',['bestT',-1],ao)
    base = self.addDependentOption(t,boosters,['baseLearner',None],ao)
    fallback = self.addDependentOption(t,'trbagg',['fallbackLearner',None],ao)
    if remainingDepth > 0:
      self.setupClassifier(None,base,remainingDepth-1)
      self.setupClassifier(None,fallback,remainingDepth-1)


  def setupPlanner(self):
    p = self.addDependentOption(self.adhoc,['mcts','uct'],['planner',None])
    self.addOption('silver',False,p)
    self.addOption('weighted',True,p)
    self.addOption('update','polynomial',p)
    self.addOption('lambda',0.8,p)
    self.addOption('gamma',0.95,p)
    self.addOption('unseenValue',999999,p)
    self.addOption('initialValue',0,p)
    self.addOption('initialStateVisits',0,p)
    self.addOption('initialStateActionVisits',0,p)
    self.addOption('time',0,p)
    self.addOption('rewardBound',0.5,p)
    self.addOption('playouts',1000,p)
    self.addOption('depth',100,p)
    self.addOption('pruningMemory',-1,p)
    self.addOption('theoreticallyCorrectLambda',False,p)
    self.addOption('student','$(STUDENT)',p)
    self.addOption('students','data/students.txt',p)
    x = self.addOption('modelOutputFile','',p)
    x.setFlags(QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled)

    self.models = self.addOption('models',None,p)
    self.setupModels()

  def setupModels(self):
    self.addModel('GR','random','gr')
    self.addModel('TA','random','ta')
    self.addModel('GP','random','gp')
    self.addModel('PD','random','pd')
    self.addModel('Classifier','random','classifier')

  def addModel(self,desc,prey,pred):
    x = self.addOption(desc,None,self.models)
    self.addOption('prob',1.0,x)
    self.addOption('desc',desc,x)
    self.setupAgent('prey',prey,x)
    self.setupAgent('predator',pred,x)
    x.setExpanded(False)
    self.tree.models[x] = True
    return x

def save(parent,tree):
  dialog = QtGui.QFileDialog(parent,directory='configs/',filter='*.json')
  dialog.fileSelected.connect(lambda f: tree.output(f))
  dialog.show()

class ConfigEditor(QtGui.QWidget):
  def __init__(self,inFile,outFile):
    super(ConfigEditor, self).__init__()
    
    tree = Tree()
    o = Options(tree)
    tree.options = o
    if inFile is not None:
      tree.read(inFile)
    tree.setViews(None)

    modelButton = QtGui.QPushButton("Add Model")
    modelButton.clicked.connect(lambda: o.addModel('New','random','gr'))
    saveButton = QtGui.QPushButton("Save")
    saveButton.clicked.connect(lambda: save(self,tree))
    #saveButton.clicked.connect(lambda: tree.output(outFile))
    printButton = QtGui.QPushButton("Print")
    printButton.clicked.connect(lambda: tree.output(None))
    
    layout = QtGui.QVBoxLayout()
    layout.addWidget(tree.tree)
    hbox = QtGui.QHBoxLayout()
    layout.addLayout(hbox)
    self.setLayout(layout)
    
    hbox.addWidget(modelButton)
    hbox.addWidget(printButton)
    hbox.addWidget(saveButton)
    
    self.setWindowTitle('Config Editor')
    self.resize(800,800)

def main(args,inFile,outFile):
  app = QtGui.QApplication(args)
  win = ConfigEditor(inFile,outFile)
  win.show()
  app.exec_()

if __name__ == '__main__':
  from optparse import OptionParser
  parser = OptionParser()
  #parser.add_option('-i','--in',dest='inFile',help='input file',metavar='FILE',default=None)
  parser.add_option('-o','--out',dest='outFile',help='output file',metavar='FILE',default=None)
  options,args = parser.parse_args()
  assert(len(args) <= 1)
  inFile = None
  if len(args) >= 1:
    inFile = args[0]
  main(args,inFile,options.outFile)
