# AI primarily used for help with documentation, formatting, and in-line comments. Some debugging/intermediate fallback error logic help was also taken.
# Some prompting of AI for things like this README and user prompting (e.g. report message prompting) also used some AI assistance.
# The evaluation part was also partially AI-assisted

# Eval results:
Confusion Matrix:
               | Predicted No | Predicted Yes
True No        | 68 (TN)     | 55 (FP)
True Yes       | 6 (FN)     | 71 (TP)

Metrics:
Accuracy:  0.6950
Precision: 0.5635
Recall:    0.9221
F1 Score:  0.6995
Confusion matrix visualization saved as 'confusion_matrix.png'

Detailed Classification Report:
                 precision    recall  f1-score   support

Not Hate Speech       0.92      0.55      0.69       123
    Hate Speech       0.56      0.92      0.70        77

       accuracy                           0.69       200
      macro avg       0.74      0.74      0.69       200
   weighted avg       0.78      0.69      0.69       200


Sample False Positives (Non-hate speech classified as hate speech):
1. "Nothing justifies the existence of any Muslim country.  All Muslim land is stolen land...." - Explanation: The text contains hate speech directed towards Muslims by stating that the existence of any Muslim c...
2. "This is an invasion: we cannot coexist with millions of strangers that do not want to integrate...." - Explanation: The text expresses a negative and discriminatory attitude towards a group of people based on their s...
3. "I'm not sexist but also definitely not a fan of the rumour of Ghostbusters 3 with women. What next? ..." - Explanation: The statement expresses a negative sentiment towards the idea of a Ghostbusters movie with women, im...
4. "1400 years ago Islam stole all women's rights and turned them into slaves forever...." - Explanation: The text contains hate speech towards Islam by making a false and derogatory statement about the rel...
5. "Islam is a cancer on the European culture...." - Explanation: The statement 'Islam is a cancer on the European culture' is considered hate speech as it dehumanize...

Sample False Negatives (Hate speech not detected):
1. "Many Muslims prefer the violence of jihad...." - Explanation: The statement does not contain hate speech. It mentions a preference for violence in the context of ...
2. "There is absolutely no reason for Israel to give up an inch of land since that will get them nothing..." - Explanation: The text expresses a political opinion regarding land disputes between Israel and Muslims, but does ...
3. "I'm not sexist but the women commentator on sky sports is shocking..." - Explanation: The statement does not contain explicit hate speech but expresses criticism towards a specific woman...
4. "call me sexist if you want, but I find female sportscasters really annoying...." - Explanation: The statement expresses a personal opinion about finding female sportscasters annoying, but it does ...
5. "The only thing a woman should help a man build is a relationship #tbh #nosexist..." - Explanation: The text does not contain hate speech. It expresses an opinion about gender roles in relationships b...

Evaluation completed.