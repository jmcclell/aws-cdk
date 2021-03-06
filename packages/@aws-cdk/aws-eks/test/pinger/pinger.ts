import * as ec2 from '@aws-cdk/aws-ec2';
import * as lambda from '@aws-cdk/aws-lambda';
import { Construct, CustomResource, Token, Duration } from '@aws-cdk/core';
import * as cr from '@aws-cdk/custom-resources';

export interface PingerProps {
  readonly url: string;
  readonly securityGroup?: ec2.SecurityGroup;
  readonly vpc?: ec2.Vpc;
}
export class Pinger extends Construct {

  private _resource: CustomResource;

  constructor(scope: Construct, id: string, props: PingerProps) {
    super(scope, id);

    const func = new lambda.Function(this, 'Function', {
      code: lambda.Code.fromAsset(`${__dirname}/function`),
      handler: 'index.handler',
      runtime: lambda.Runtime.PYTHON_3_6,
      vpc: props.vpc,
      securityGroups: props.securityGroup ? [props.securityGroup] : undefined,
      timeout: Duration.minutes(10),
    });

    const provider = new cr.Provider(this, 'Provider', {
      onEventHandler: func,
    });

    this._resource = new CustomResource(this, 'Resource', {
      serviceToken: provider.serviceToken,
      properties: {
        Url: props.url,
      },
    });
  }

  public get response() {
    return Token.asString(this._resource.getAtt('Value'));
  }

}