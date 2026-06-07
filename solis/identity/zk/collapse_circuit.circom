template CollapseCheckFixed() {
    signal input entropy;
    signal input magnetic;
    signal input fusion;
    signal output collapse;

    collapse <== entropy * (1 - magnetic) * fusion;
}

component main = CollapseCheckFixed();
