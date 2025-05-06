#include <stdio.h>
#include <stdlib.h>

char secret[] = "s3cret_t4rget2";

void print_secret() {
    printf("%s\n", secret);
}

int main() {
    printf("Secret string: ");
    print_secret();
    return 0;
} 