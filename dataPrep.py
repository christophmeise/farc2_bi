from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns
from sklearn.feature_selection import SelectPercentile
from sklearn.feature_selection import chi2
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import Binarizer, scale
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import confusion_matrix
from sklearn.cross_validation import KFold
from sklearn import cross_validation as cv
from sklearn import tree
from sklearn import naive_bayes
from sklearn.ensemble import RandomForestClassifier as RF

featureSelectionType = "decision" #chi or decision
printToCSV = True

train = ""
test = ""
X_train = ""
X_test = ""
y_train = ""
y_test = ""
predictedValues = []

def main():
    print("CSV Mode activated: "+str(printToCSV))
    print("Feature Selection Type: "+str(featureSelectionType))
    initializeData()
    dataUnderstanding()
    dataPreparation()
    modeling()
    evaluation()

def initializeData():
    print('STEP 0: Reading data')
    global train
    global test
    train = pd.read_csv("./Data/train.csv")
    test = pd.read_csv("./Data/test.csv")
 
def dataUnderstanding():
    print('STEP 1: Data Understanding')
    f = open('00_data_understanding.info', 'w+')
    train.info(verbose=True, null_counts=True, buf=f)
    f.writelines('-----Zielvariablenbeschreibung------\n')
    f.writelines(str(train["TARGET"].describe()))
    f.writelines(str(train["TARGET"].unique()) + '\n')
    anzahl = train["TARGET"].value_counts()
    f.writelines("Anzahl Satisfied: " + str(anzahl[0])+ '\n')
    f.writelines("Anzahl Unsatisfied: " + str(anzahl[1])+ '\n')
    f.writelines("Anzahl in Prozent: " + str((anzahl[0]/(anzahl[0]+anzahl[1]))*100) + "%.\n")
    f.writelines(str(countDistinct()) + " Spalten beinhalten keine unterschiedlichen Werte!\n")
    f.writelines(str(countStrings()) + " Spalten beinhalten String Werte!\n")
    f.writelines(str(train.isnull().values.sum()) + " null-Werte sind insgesamt im Datensatz enthalten!\n")
    for column in train:
        f.writelines(str(column) + "  Max Wert: " + str(train[column].max()) + "   Min Werte:  " + str(train[column].min())+ '\n')
    f.close()

    sns.countplot(train["TARGET"])
    plt.savefig('./Generated_Visualization/targetBarchart.png')
    print('Written data understanding file.')
    print('Generated barchart.')

def dataPreparation():
    print("STEP 2 :Data preparation")
    global train
    removeConstantColumns(train)
    removeDuplicatedColumns(train)
    printToCSVWithFilename(train, '01_train_cleanup.csv')
    deleteColumnsWithHighCorrelation(train)
    printToCSVWithFilename(train, '02_train_remove_high_correlation.csv')
    splitDataset()
    featureSelection()
    printToCSVWithFilename(train, '03_train_f_sel_decision_tree.csv')
    dataVisualization()
    removeRowsMissingValues()
    printToCSVWithFilename(train, '04_train_after_datapreperation.csv')
    #### data cleansing is not necessary in our case, only numeric values
    #### normalizing is not necessarry
    
def modeling():
    print('STEP 3: Modeling')
    global predictedValues
    global test
    feature_names = train.columns.tolist()
    feature_names.remove('TARGET')
    Z = test[feature_names]
    X = train[feature_names]
    y = train['TARGET']
    skf = cv.StratifiedKFold(y, n_folds=3, shuffle=True, random_state=1337 )
    score_metric = 'roc_auc'
    scores = {}
    
    def score_model(model, title):
        predicted = cv.cross_val_predict(model, X, y, cv=skf)
        predictedValues.append([title, predicted])
        return cv.cross_val_score(model, X, y, cv=skf, scoring=score_metric)
    
    print('Logistic Regression...')
    scores['logistic'] = score_model(LogisticRegression(random_state=1337), 'logistic_regression')
    print('Decision Tree Classifier...')
    scores['tree'] = score_model(tree.DecisionTreeClassifier(random_state=1337), 'decision_tree_classifier')
    print('Naive Bayes Gaussian Classifier...')
    scores['gaussian'] = score_model(naive_bayes.GaussianNB(), 'naive_bayes_gaussian_classifier')

    clf = tree.DecisionTreeClassifier(random_state=1337)
    clf.fit(X, y)
    tree.export_graphviz(clf,out_file='tree.dot')  

    test_predictions = pd.DataFrame(clf.predict_proba(Z))
    test_predictions.to_csv('test_predictions_decisionTree.csv', index=True)

    clf = LogisticRegression(random_state=1337)
    clf.fit(X,y)
    test_predictions = pd.DataFrame(clf.predict_proba(Z))
    test_predictions.to_csv('test_predictions_logisticRegression.csv', index=True)

    clf = naive_bayes.GaussianNB()
    clf.fit(X,y)
    test_predictions = pd.DataFrame(clf.predict_proba(Z))
    test_predictions.to_csv('test_predictions_naiveBayes.csv', index=True)

    model_scores = pd.DataFrame(scores).mean()
    model_scores.sort_values(ascending=False)
    model_scores.to_csv('model_scores.csv', index=True)
    print('Model scores\n{}'.format(model_scores))

def evaluation():
    print('STEP 4: Evaluation')
    for predicted in predictedValues:
        confusionMatrix(predicted)
 
############################################################################## 

def removeConstantColumns(train):
    numberOfColumnsBefore = train.columns.shape[0]
    remove = []
    for col in train.columns:
        if train[col].std() == 0:
            remove.append(col)
    train.drop(remove, axis=1, inplace=True)
    numberOfColumnsAfter = train.columns.shape[0]
    print("Removed "+str(numberOfColumnsBefore-numberOfColumnsAfter)+" constant columns.")
    
def removeDuplicatedColumns(train):
    numberOfColumnsBefore = train.columns.shape[0]
    remove = []
    cols = train.columns
    for i in range(len(cols)-1):
        v = train[cols[i]].values
        for j in range(i+1,len(cols)):
            if np.array_equal(v,train[cols[j]].values):
                remove.append(cols[j])
    train.drop(remove, axis=1, inplace=True)
    numberOfColumnsAfter = train.columns.shape[0]
    print("Removed "+str(numberOfColumnsBefore-numberOfColumnsAfter)+" duplicated columns.")
    
def deleteColumnsWithHighCorrelation(data):
    max_cor = 0.8
    numberOfColumnsBefore = train.columns.shape[0]
    corr_matrix = data.corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(np.bool))
    to_drop = [column for column in upper.columns if any(upper[column] > max_cor)]
    for col in to_drop:
        del data[col]
    numberOfColumnsAfter = train.columns.shape[0]
    print("Removed "+str(numberOfColumnsBefore-numberOfColumnsAfter)+" columns with correlation > "+str(max_cor)+".")

def removeRowsMissingValues():
    numberOfRowsBefore = train.shape[0]
    for index, row in train.iterrows():
        for column in train:
            if row[column] == -999999 or row[column] == 999999 or row[column] == 9999999999 or row[column] == -9999999999:
                train.drop(index, inplace = True)
                break
    numberOfRowsAfter = train.shape[0]
    print("Removed "+str(numberOfRowsBefore-numberOfRowsAfter)+" rows with missing values.")

def featureSelection():    
    if featureSelectionType == "chi":
        chiSquared()
    if featureSelectionType == "decision":
        decisionTree()

def decisionTree():
    print('Feature selection with decision tree.')
    global test
    global train

    numberOfFeatures = 20
    clf = ExtraTreesClassifier(random_state=1729)
    selector = clf.fit(X_train, y_train)
    feat_imp = pd.Series(clf.feature_importances_, index = X_train.columns.values).sort_values(ascending=False)
    importantFeatures = feat_imp[:numberOfFeatures]
    print('Selected Features ('+str(numberOfFeatures)+') are:\n'+str(importantFeatures))
    
    train = train[importantFeatures.index.tolist()+['TARGET']]
    test = test[importantFeatures.index.tolist()]

def chiSquared():
    print('Feature selection with chi squared...')
    global train
    global test
    data = train.iloc[:,:-1]
    y = train.TARGET
    ## see https://www.kaggle.com/cast42/exploring-features/notebook
    ## used as comparison to our decision tree
    binarizedData = Binarizer().fit_transform(scale(data))
    selectChi2 = SelectPercentile(chi2, percentile=3).fit(binarizedData, y)
    
    chi2_selected = selectChi2.get_support()
    chi2_selected_features = [ f for i,f in enumerate(data.columns) if chi2_selected[i]]
    print('Chi2 selected {} features {}.'.format(chi2_selected.sum(),
       chi2_selected_features))
    train = train[chi2_selected_features+['TARGET']]
    test = test[chi2_selected_features]
    
def dataVisualization():
    ## Heatmap visualization of correlations
    sns.heatmap(train.corr())
    plt.savefig('./Generated_Visualization/heatmap.png')
    plt.clf()
    i = 0
    for column in train:
        if len(train[column].unique()) < 10 and column != "TARGET":
            sns.countplot(train[column])
            plt.savefig('./Generated_Visualization/column'+str(i)+'.png')
            plt.clf()
            i = i + 1
    ## Visualizing the top 2 features
    ## inspired by competition winner https://www.kaggle.com/cast42/exploring-features/notebook
    train['var15'].hist(bins=100)
    plt.savefig('./Generated_Visualization/var15.png')
    plt.clf()
    sns.FacetGrid(train, hue="TARGET", size=6).map(sns.kdeplot, "var15").add_legend()
    plt.title('Unhappy customers are slightly older')
    plt.savefig('./Generated_Visualization/var15ByTarget.png')
    plt.clf()
    sns.FacetGrid(train, hue="TARGET", size=6).map(sns.kdeplot, "var36").add_legend()
    plt.savefig('./Generated_Visualization/var36dist.png')
    plt.clf()

    
def confusionMatrix(y_pred):
    y_actu = train['TARGET'].values
    confusion_matrix(y_actu, y_pred[1])    
    y_actu = pd.Series(y_actu, name='Actual')
    y_pred_data = pd.Series(y_pred[1], name='Predicted')
    df_confusion = pd.crosstab(y_actu, y_pred_data, rownames=['Actual'], colnames=['Predicted'], margins=True)
    plot_confusion_matrix(df_confusion, y_pred[0])
    df_confusion = df_confusion.astype(float)
    df_confusion.values[0, 0] = df_confusion.values[0, 0] / df_confusion.values[0, 2]
    df_confusion.values[0, 1] = df_confusion.values[0, 1] / df_confusion.values[0, 2]
    df_confusion.values[1, 0] = df_confusion.values[1, 0] / df_confusion.values[1, 2]
    df_confusion.values[1, 1] = df_confusion.values[1, 1] / df_confusion.values[1, 2]
    plot_confusion_matrix(df_confusion, str(y_pred[0])+'probability')
    # classifier predicted a customer churn and they didn't -> its forgivable
    # clas. predicted customer to return, didn't act, and then they churned ->really bad
    benefitFalsePositive = -10   ## SUNK COSTS - churn predicted, but customer stays
    benefitFalseNegative = 0 ## LOST MONEY FROM CUSTOMER (same as true positve, just reverse, not rewarding twice) - churn not predicted, but customer left
    benefitTruePositive = 10000 ## MONEY GAINED FROM KEEPING CUSTOMER - churn predicted and customer wanted to churn
    benefitTrueNegative = 0 ## NO COSTS NO GAINS - no churn predicted, and no churn
    probabilityP = df_confusion.values[1, 2] / df_confusion.values[2, 2]
    probabilityN = df_confusion.values[0, 2] / df_confusion.values[2, 2]
    df_confusion.values[0, 0] = df_confusion.values[0, 0] * benefitTrueNegative * probabilityN
    df_confusion.values[0, 1] = df_confusion.values[0, 1] * benefitFalseNegative * probabilityP
    df_confusion.values[1, 0] = df_confusion.values[1, 0] * benefitFalsePositive * probabilityN
    df_confusion.values[1, 1] = df_confusion.values[1, 1] * benefitTruePositive * probabilityP
    plot_confusion_matrix(df_confusion, str(y_pred[0])+'profit')
    profit = df_confusion.values[0, 0] + df_confusion.values[0, 1] + df_confusion.values[1, 0] + df_confusion.values[1, 1]
    print('Expected profit with model '+str(y_pred[0])+' is '+str(profit))
    print('Generated confusion matrices.')
    
##############################################################################
    
def plot_confusion_matrix(df_confusion, title):
    cmap='rainbow'
    plt.matshow(df_confusion, cmap=cmap)
    #plt.title(title)
    plt.colorbar()
    tick_marks = np.arange(len(df_confusion.columns))
    plt.xticks(tick_marks, df_confusion.columns, rotation=45)
    plt.yticks(tick_marks, df_confusion.index)
    #plt.tight_layout()
    plt.ylabel(df_confusion.index.name)
    plt.xlabel(df_confusion.columns.name)
    # Loop over data dimensions and create text annotations.
    for i in range(len(df_confusion.columns)):
        for j in range(len(df_confusion.index)):
            text = plt.text(j, i, f'{df_confusion.values[i, j]:.3f}',
                           ha="center", va="center", color="w")
    plt.savefig('./Generated_Visualization/confusionMatrix'+str(title)+'.png')

def splitDataset():
    global X_train
    global X_test
    global y_train
    global y_test
    X_train, X_test, y_train, y_test = train_test_split(train.drop(["TARGET","ID"],axis=1), train.TARGET.values, test_size=0.20, random_state=1729)

def printToCSVWithFilename(data, filename):
    if printToCSV:
        data.to_csv(filename, sep=';', encoding='utf-8')

def histogram(data, x_label, y_label, title):
    _, ax = plt.subplots()
    ax.hist(data, color = '#539caf')
    ax.set_ylabel(y_label)
    ax.set_xlabel(x_label)
    ax.set_title(title)

def countDistinct():
    dist_counter = 0
    for column in train:
        if len(train[column].unique()) < 2:
            dist_counter = dist_counter + 1
    return dist_counter

def countStrings():
    string_counter = 0
    for column in train:
        for i in train[column]:
            if type(i) is str:
                print(column)
                string_counter = string_counter + 1
    return string_counter

main()
