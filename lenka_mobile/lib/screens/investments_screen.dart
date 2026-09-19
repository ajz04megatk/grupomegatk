import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../core/lenka_api_client.dart';

class InvestmentsScreen extends StatelessWidget {
  const InvestmentsScreen({super.key, required this.api}); final LenkaApiClient api;
  String money(dynamic v) => NumberFormat('#,##0.00').format((v as num?) ?? 0);
  @override Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('Mis inversiones')), body: FutureBuilder<List<dynamic>>(
    future: api.investments(), builder: (context, snapshot) {
      if (snapshot.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
      if (snapshot.hasError) return const Center(child: Text('No fue posible cargar las inversiones.'));
      final rows=snapshot.data??[]; if(rows.isEmpty) return const Center(child: Text('No tienes inversiones registradas.'));
      return ListView.builder(padding: const EdgeInsets.all(12), itemCount: rows.length, itemBuilder:(context,index){
        final r=Map<String,dynamic>.from(rows[index] as Map);
        return Card(child: ListTile(leading: const Icon(Icons.savings_outlined), title: Text(r['name'].toString()),
          subtitle: Text('Capital: '+r['currency'].toString()+' '+money(r['outstanding_principal'])+'\nInteres acumulado: '+money(r['accrued_interest'])+' | Tasa: '+r['passive_rate'].toString()+'%'),
          isThreeLine:true, trailing: const Icon(Icons.chevron_right), onTap:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>InvestmentDetailScreen(api:api,investmentId:r['id'] as int)))));
      });
    }));
}

class InvestmentDetailScreen extends StatelessWidget {
  const InvestmentDetailScreen({super.key,required this.api,required this.investmentId}); final LenkaApiClient api; final int investmentId;
  String money(dynamic v)=>NumberFormat('#,##0.00').format((v as num?)??0);
  @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('Detalle de inversion')),body:FutureBuilder<Map<String,dynamic>>(
    future:api.investmentDetail(investmentId),builder:(context,snapshot){
      if(snapshot.connectionState!=ConnectionState.done)return const Center(child:CircularProgressIndicator());
      if(snapshot.hasError)return const Center(child:Text('No fue posible cargar el detalle.'));
      final d=snapshot.data!; final interest=List<dynamic>.from(d['interest_history'] as List? ?? []);
      return ListView(padding:const EdgeInsets.all(16),children:[
        Text(d['name'].toString(),style:Theme.of(context).textTheme.headlineSmall),const SizedBox(height:8),
        Text('Capital vigente: '+d['currency'].toString()+' '+money(d['outstanding_principal'])),
        Text('Interes acumulado: '+d['currency'].toString()+' '+money(d['accrued_interest'])),
        Text('Tasa contractual: '+d['passive_rate'].toString()+'% '+d['rate_period'].toString()),
        Text('Tasa retiro anticipado: '+d['early_withdrawal_rate'].toString()+'% '+d['rate_period'].toString()),
        Text('Vencimiento: '+(d['maturity_date']??'No definido').toString()),const SizedBox(height:22),
        Text('Capitalizacion de intereses',style:Theme.of(context).textTheme.titleLarge),
        ...interest.map((item){final l=Map<String,dynamic>.from(item as Map);return ListTile(contentPadding:EdgeInsets.zero,title:Text(l['date'].toString()),subtitle:Text('Base: '+money(l['base_amount'])+' | Tasa: '+l['rate'].toString()+'%'),trailing:Text(d['currency'].toString()+' '+money(l['amount'])));}),
      ]);
    }));
}
