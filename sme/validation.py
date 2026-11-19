"""Explicit rolling train/test runner. Selection, when requested, uses train data only."""
from datetime import timedelta
from .engine import Engine


def walk_forward(bars,configs,instrument='EURUSD',train_days=730,test_days=365,conversion=None):
    if not bars or train_days<=0 or test_days<=0 or not configs:
        raise ValueError('Nonempty bars/configurations and positive windows required')
    folds=[]
    start=bars[0].time
    while True:
        split=start+timedelta(days=train_days)
        end=split+timedelta(days=test_days)
        if split>bars[-1].time:
            break
        train=[b for b in bars if start<=b.time<split]
        test=[b for b in bars if split<=b.time<end]
        if not train or not test:
            break
        training=[Engine(c,instrument,conversion=conversion).run(train) for c in configs]
        # Candidates with no closed trades are ineligible for selection, unless only one fixed config.
        eligible=[i for i,r in enumerate(training) if r['metrics']['completed_trades']]
        if len(configs)>1 and not eligible:
            folds.append(dict(train_start=start.isoformat(),test_start=split.isoformat(),skipped='no_training_trades'))
        else:
            selected=max(eligible,key=lambda i:training[i]['metrics']['average_r']) if len(configs)>1 else 0
            result=Engine(configs[selected],instrument,conversion=conversion).run(test)
            folds.append(dict(train_start=start.isoformat(),train_end=split.isoformat(),test_start=split.isoformat(),
                              test_end=min(end,bars[-1].time+timedelta(hours=1)).isoformat(),selected_index=selected,
                              selection='maximum train-only mean R' if len(configs)>1 else 'fixed configuration; no optimization',
                              train_metrics=training[selected]['metrics'],test_metrics=result['metrics']))
        start+=timedelta(days=test_days)
    return dict(folds=folds,note='Each train/test run restarts flat and cold-warms MAs. No position is carried across folds. Partial last fold is labelled by end date.')
