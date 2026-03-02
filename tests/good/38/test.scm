(let ((my-cons (lambda (x y) (cons x y))))
    (car (foldl my-cons '() (list 1 2 3))))