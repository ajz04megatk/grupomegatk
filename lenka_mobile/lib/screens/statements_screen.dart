import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../core/lenka_api_client.dart';

class StatementsScreen extends StatelessWidget {
  const StatementsScreen({super.key,required this.api}); final LenkaApiClient api;
  String money(dynamic v)=>NumberFormat('#,##0.00').format((v as num?)??0);
  @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('Estados de cuenta')),body:FutureBuilder<List<dynamic>>(
    future:api.statements(),builder:(context,snapshot){
      if(snapshot.connectionState!=ConnectionState.done)return const Center(child:CircularProgressIndicator());
      if(snapshot.hasError)return const Center(child:Text('No fue posible cargar los estados de cuenta.'));
      final rows=snapshot.data??[];if(rows.isEmpty)return const Center(child:Text('Aun no tienes estados de cuenta generados.'));
      return ListView.builder(padding:const EdgeInsets.all(12),itemCount:rows.length,itemBuilder:(context,index){
        final r=Map<String,dynamic>.from(rows[index] as Map);
        return Card(child:ListTile(leading:const Icon(Icons.receipt_long_outlined),title:Text(r['name'].toString()),
          subtitle:Text(r['date_from'].toString()+' a '+r['date_to'].toString()+'\nSaldo final: '+r['currency'].toString()+' '+money(r['closing_balance'])),isThreeLine:true));
      });
    }));
}
