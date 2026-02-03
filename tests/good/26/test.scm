(let ((b 2))
    (let ((a (lambda (y) (+ y b))))
        (+ (a 1) (a 1))))