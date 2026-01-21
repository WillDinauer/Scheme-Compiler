(let ((a 3) (b 4))
    (+ a (+ b (let ((a 5) (c 6))
        (- c a)))))