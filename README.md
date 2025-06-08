# CS 152 - Trust and Safety Engineering

Link the demo video used for presentation can be found here: https://drive.google.com/file/d/1ntUUyr7FKFRo3bhFw0H4ttBkq4kcelKW/view

Note: We intentionally made the video shorter for the sake of the presentation. More details about our technical implementation can be found in this doc. 

# Technical Backend

## Regex

## OpenAI call with prompting

### Eval for just OpenAI call

#### Utilizing dataset from class (startup) \\

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


#### Utilizing Civil Comments Dataset (with specific prompting)

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

#### Utilizing Civil Comments Dataset (without specific prompting)

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

### Supabase

Our moderator bot maintains an internal database for tracking report history. The database is built using Supabase, an abstraction layer on PostgreSQL. We chose to use this database for its simplicity and reliability.
When a user’s message is reported, our bot queries the database for past reports regarding this user. It provides this as context to the moderator. As seen in the moderator flow diagram, part of the message sent to the moderator contains “User Offense History.” The more reports a user has had filed against them, the stronger the model suggests that the moderator take action.  

### Eval for everything

Can be found in poster. An improvement that can be made to our final setup is that instead of making an openai call if there is no match, instead we only make an openai call if there is a match to evaluation for context. However, this requires us to include misspelled words in our regex dataset which we would theoretically need to create overtime as more mispellings of slurs arise.