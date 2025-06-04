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

# Civil Comments Threat Dataset Evaluation (with specific prompting)

Confusion Matrix:
               | Predicted No | Predicted Yes
True No        | 95 (TN)     | 5 (FP)
True Yes       | 37 (FN)     | 63 (TP)

Metrics:
Accuracy:  0.7900
Precision: 0.9265
Recall:    0.6300
F1 Score:  0.7500
Confusion matrix visualization saved as 'confusion_matrix.png'

Detailed Classification Report:
                 precision    recall  f1-score   support

Not Hate Speech       0.72      0.95      0.82       100
    Hate Speech       0.93      0.63      0.75       100

       accuracy                           0.79       200
      macro avg       0.82      0.79      0.78       200
   weighted avg       0.82      0.79      0.78       200


Sample False Positives (Non-hate speech classified as hate speech):
1. "@Rmiller101 - Spoken like a true elitist. But look out bud. The re-awakening in Europe, Brexit and n..." - Explanation: The statement 'The unwashed masses are coming for you and your ilk' can be interpreted as a threat o...
2. "'Work together'? Dream on. The liberals are already busy creating the next scandal/crime to accuse P..." - Explanation: The text contains threatening language towards a specific group of people, referring to them as 'sni...
3. "States rights and white supremacy are not mutually exclusive. The state right that was being defende..." - Explanation: The text contains references to white supremacy, racial discrimination, and violence against black p...
4. "Somebody needs to dig up the Peterson's back yard!  What other evil deeds did Monster Mom hide to pr..." - Explanation: The text contains a threatening statement suggesting that someone should dig up the Peterson's backy...
5. "Perps are showing up a lot more often these days. We need laws to reflect current day crimes. Like e..." - Explanation: The text contains a clear call for violent action ('execute when guilty') without due process, which...

Sample False Negatives (Hate speech not detected):
1. "Third time. Magic. In the real world, marriages end and the ones that follow, as long as they were n..." - Explanation: No hate speech or threats detected in the text provided....
2. "If you consider shooting oneself in the mouth with a Luger "getting away with it...".  Perhaps compa..." - Explanation: The text does not contain hate speech or threats. It appears to be discussing a method of suicide, b...
3. "Racism maims and kills...." - Explanation: The text does not contain hate speech or threats. It is a statement condemning racism and its harmfu...
4. "Gun is a weapon that can kill. Newspapers cannot be used to kill even when a rolled up one is used t..." - Explanation: No hate speech or threats detected in the text. The mention of a gun as a weapon and a newspaper bei...
5. "Immigration attorneys are going to make a killing off immigrants and their proxies going forward..." - Explanation: No hate speech or threats detected in the text. The statement is discussing a potential financial ga...

# Civil Comments Threat Dataset Evaluation (without specific prompting)

Confusion Matrix:
               | Predicted No | Predicted Yes
True No        | 93 (TN)     | 7 (FP)
True Yes       | 46 (FN)     | 54 (TP)

Metrics:
Accuracy:  0.7350
Precision: 0.8852
Recall:    0.5400
F1 Score:  0.6708
Confusion matrix visualization saved as 'confusion_matrix.png'

Detailed Classification Report:
                 precision    recall  f1-score   support

Not Hate Speech       0.67      0.93      0.78       100
    Hate Speech       0.89      0.54      0.67       100

       accuracy                           0.73       200
      macro avg       0.78      0.74      0.72       200
   weighted avg       0.78      0.73      0.72       200


Sample False Positives (Non-hate speech classified as hate speech):
1. "@Rmiller101 - Spoken like a true elitist. But look out bud. The re-awakening in Europe, Brexit and n..." - Explanation: The text contains a veiled threat towards a specific group of people ('elitist') by suggesting that ...
2. "'Work together'? Dream on. The liberals are already busy creating the next scandal/crime to accuse P..." - Explanation: The text contains threatening language towards a specific group (liberals) by calling them 'snivelin...
3. "Between racist Eastman and 'Slappy' Wilson the Wasilla delegation is an embarassment to the valley a..." - Explanation: The text contains hate speech targeting individuals based on their race and political affiliation, a...
4. "This is an appalling decision in allowing the takeover of a high tech firm by businesses linked to t..." - Explanation: The text contains hate speech towards the communist party of China, referring to them as corrupt, op...
5. "States rights and white supremacy are not mutually exclusive. The state right that was being defende..." - Explanation: The text contains hate speech related to racism, white supremacy, and discrimination against certain...

Sample False Negatives (Hate speech not detected):
1. "Third time. Magic. In the real world, marriages end and the ones that follow, as long as they were n..." - Explanation: The text does not contain hate speech or threats. It discusses marriages and does not target any spe...
2. "If you consider shooting oneself in the mouth with a Luger "getting away with it...".  Perhaps compa..." - Explanation: The text does not contain hate speech or threats. It seems to be discussing methods of suicide, but ...
3. "Racism maims and kills...." - Explanation: The text does not contain hate speech or threats. It is a statement highlighting the harmful effects...
4. "I am not going to buy anything for 3 years, until the GET goes back down.  I am going to starve out ..." - Explanation: The text does not contain hate speech or threats. It expresses frustration and a decision to withhol...
5. "The next time any of my kids say something sassy, I'm going to pile-drive them into the floor face f..." - Explanation: The text contains a violent statement but does not include hate speech or threats towards a specific...