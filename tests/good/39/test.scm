(let ((my-cons (lambda (x y) (cons x y))))
    (car (foldr my-cons '() (list 1 2 3))))