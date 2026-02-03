(let ((b 2))
    (let ((a (lambda (y) (cons (let ((z 10)) (lambda () (+ y z))) (lambda (c) (- c b))))))
        ((car (a 5)))))