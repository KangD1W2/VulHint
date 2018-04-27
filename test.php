<?php

$test_include = "test_include.php";

if (file_exists($test_include)) {
    include $test_include;/*vvv*/
}

$id = $_GET['id'];/*vvv*/

$sql = "SELECT * FROM dual WHERE id=$id";

$sql = "SELECT * FROM dual WHERE id={$id}";/*vvv*/

$sql = "SELECT * FROM dual WHERE id = {$id}";/*vvv*/

$sql2 = "SELECT * FROM dual WHERE id='{$id}'";

