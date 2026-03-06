(let* ((a (lambda (x) (+ x 5))) (b (a 10)) (c (lambda (x) (* b x))))
    (c 5))