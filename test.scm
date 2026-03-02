(let ((a 1) (b 3))
    (let ((a (if #t b a)))
        (if #t a b)))