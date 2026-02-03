(let ((b 2))
    (let ((a (lambda (y) (cons (let ((z 30)) (lambda () (+ y z))) (lambda (c) (- c b))))))
        (let ((x (cdr (a 20))))
            (x 3))))