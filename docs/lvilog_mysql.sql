CREATE TABLE lvilog (
    id INT(10) UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    aika DATETIME NOT NULL, 
    menovesi DECIMAL(5,2),
    tulovesi DECIMAL(5,2),
    ulkolampo DECIMAL(5,2),
    var_yla DECIMAL(5,2),
    var_keski DECIMAL(5,2),
    var_ala DECIMAL(5,2),
    yla_tulo DECIMAL(5,2),
    maaliuos_tulo DECIMAL(5,2), 
    maaliuos_lahto DECIMAL(5,2),
    tilatieto INT(11)
);  

CREATE INDEX i_lvilog_aika ON lvilog (aika);
