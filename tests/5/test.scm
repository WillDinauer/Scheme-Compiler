(let ((a 1) (b 3))
    (let ((a (if (= a 3) #\a #\b)))
        (if (= 4 (+ 1 b)) a #\r)))