(let ((f (lambda () (quote (cons 1 #\H)))))
    (eq? (f) (f)))