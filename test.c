#include <stdio.h>
#include <stdlib.h>


struct node{
    int data;
    struct node* next;
};


int main(){
    // first we will make nodes
    struct node* first = (struct node*)malloc(sizeof(struct node));
    struct node* second = (struct node*)malloc(sizeof(struct node));
    struct node* third = (struct node*)malloc(sizeof(struct node));

    //now we will assign the values 

    first -> data = 10;
    second -> data = 20;
    third -> data = 30;


    //link nodes

    first->next = second;
    second->next = third;
    third->next = NULL;


    //print list

    struct node* temp = first;
    while(temp!=NULL){
        printf("%d ", temp->data);
        temp = temp->next;
    }
    printf("NULL\n");
      
}